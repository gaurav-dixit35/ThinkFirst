import logging
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from apps.api import deployment
from apps.api.db import migrate, verify_schema
from apps.api.http_safety import RequestBodyLimit
from apps.api.main import private_responses
from apps.api.serve import port


def test_database_urls_and_safe_invalid_errors():
    for scheme in ('postgres', 'postgresql', 'postgresql+psycopg'):
        parsed = deployment.database_url(f'{scheme}://runtime:p%40ss@database:5432/thinkfirst?sslmode=require')
        assert parsed.drivername == 'postgresql+psycopg'
        assert parsed.password == 'p@ss'
        assert parsed.query['sslmode'] == 'require'
    with pytest.raises(ValueError) as error:
        deployment.database_url('private-password-not-a-url')
    assert 'private-password' not in str(error.value)


def test_production_startup_cannot_auto_migrate(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.delenv('AUTO_MIGRATE', raising=False)
    assert deployment.auto_migrate() is False
    monkeypatch.setenv('AUTO_MIGRATE', 'true')
    with pytest.raises(ValueError, match='separately'):
        deployment.auto_migrate()
    monkeypatch.setenv('PORT', '4567')
    assert port() == 4567
    monkeypatch.setenv('PORT', '0')
    with pytest.raises(ValueError):
        port()


def test_readiness_is_read_only_and_reports_missing_launch_settings(monkeypatch):
    settings = dict(ENVIRONMENT='production', AUTH_MODE='clerk', AUTO_MIGRATE='false',
        DATABASE_URL='postgresql://restricted:nondefault-fixture@database/thinkfirst',
        CLERK_ISSUER='https://identity.example.com', WEB_ORIGINS='https://app.example.com',
        OPERATOR_NAME='Pilot operator', SUPPORT_EMAIL='help@example.com', ADMIN_SUBJECTS='user_fixture',
        GROQ_API_KEY='synthetic-key', AI_PROVIDER='groq', AI_GLOBAL_DAILY_BUDGET_USD='1',
        AI_MAX_USD_PER_MILLION_TOKENS='10')
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    assert deployment.readiness() == []  # No network/database is required by this mode.
    monkeypatch.delenv('SUPPORT_EMAIL')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'synthetic-key')
    monkeypatch.setenv('OPENROUTER_MODEL', 'openrouter/auto')
    issues = deployment.readiness()
    assert any('SUPPORT_EMAIL' in issue for issue in issues)
    assert any('OPENROUTER_MODEL' in issue for issue in issues)
    assert all('synthetic-key' not in issue for issue in issues)


def test_schema_missing_then_migrated(tmp_path):
    engine = create_engine('sqlite:///' + str(tmp_path / 'schema.db'))
    try:
        with pytest.raises(RuntimeError, match='schema is not ready'):
            verify_schema(engine)
        migrate(engine)
        migrate(engine)  # Retry after an interrupted release must be safe.
        verify_schema(engine)
    finally:
        engine.dispose()


def test_body_limit_and_private_error_logging(caplog):
    app = FastAPI()
    app.add_middleware(RequestBodyLimit, maximum=32)
    app.middleware('http')(private_responses)

    @app.post('/save')
    def save():
        return {'saved': True}

    @app.get('/broken/{item}')
    def broken(item: str):
        raise RuntimeError('private-password private-conversation')

    with TestClient(app) as client, caplog.at_level(logging.INFO, logger='uvicorn.error'):
        assert client.post('/save', content=b'x'*32).status_code == 200
        response = client.post('/save', content=b'x'*33)
        assert response.status_code == 413
        UUID(response.headers['x-request-id'])
        response = client.get('/broken/private-id?query=private-search', headers={'Origin':'http://localhost:3000'})
        assert response.status_code == 500
        UUID(response.headers['x-request-id'])
        assert response.headers['cache-control'] == 'no-store'
        assert response.headers['access-control-allow-origin'] == 'http://localhost:3000'
        assert 'X-Request-ID' in response.headers['access-control-expose-headers']
        for private in ('private-password', 'private-conversation', 'private-id', 'private-search'):
            assert private not in response.text
            assert private not in '\n'.join(r.message for r in caplog.records if r.name == 'uvicorn.error')
        assert '/broken/{item}' in caplog.text


def test_public_contact_is_minimal(client, monkeypatch):
    monkeypatch.setenv('OPERATOR_NAME', 'Pilot operator')
    monkeypatch.setenv('SUPPORT_EMAIL', 'help@example.com')
    monkeypatch.setenv('GROQ_API_KEY', 'private-provider-key')
    response = client.get('/service-info')
    assert response.json() == {'operator':'Pilot operator', 'support_email':'help@example.com'}
    assert 'private-provider-key' not in response.text
    monkeypatch.setenv('SUPPORT_EMAIL', 'bad@example.com?body=inject')
    with pytest.raises(ValueError):
        deployment.public_info()


def test_postgres_runtime_role_cannot_rewrite_history(client):
    from contextlib import contextmanager
    from uuid import uuid4
    from sqlalchemy.exc import DBAPIError
    from apps.api.db import engine
    from apps.api.permissions import grant_runtime, verify_runtime
    if engine.dialect.name != 'postgresql':
        pytest.skip('Requires the isolated PostgreSQL test database.')
    assert engine.url.database == 'thinkfirst_test'
    role = 'thinkfirst_test_' + uuid4().hex[:16]
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.exec_driver_sql(f'CREATE ROLE {role} NOLOGIN')
            with pytest.raises(RuntimeError, match='permissions'):
                verify_runtime(conn, role)
            class Target:
                dialect = engine.dialect
                @contextmanager
                def begin(self):
                    yield conn
            grant_runtime(role, Target())
            with pytest.raises(RuntimeError, match='restricted'):
                verify_runtime(conn)  # Local fixture owner is deliberately privileged.
            conn.exec_driver_sql(f'SET LOCAL ROLE {role}')
            verify_runtime(conn)
            conn.exec_driver_sql('SELECT count(*) FROM events')
            # Runtime permits normal mutable bookkeeping without DDL permissions.
            conn.exec_driver_sql('UPDATE ai_budget_lock SET id=1 WHERE id=1')
            for statement in ('DELETE FROM events WHERE false', 'TRUNCATE events', 'ALTER TABLE events DISABLE TRIGGER immutable_events', 'CREATE TABLE public.forbidden_runtime_table(id int)'):
                with pytest.raises(DBAPIError):
                    with conn.begin_nested():
                        conn.exec_driver_sql(statement)
        finally:
            transaction.rollback()  # Includes all role creation and grants.
