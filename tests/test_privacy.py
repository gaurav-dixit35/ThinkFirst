from uuid import uuid4
from datetime import timedelta
import pytest
from sqlalchemy import select, text, func
from sqlalchemy.exc import DatabaseError
from apps.api.auth import identity
from apps.api.main import app
from apps.api.db import engine, SessionLocal, Event, Session, User, AIUsageRequest, DeletionRequest, now
from apps.api.erase import fulfill


def uid(): return str(uuid4())


@pytest.fixture
def accounts(client):
    def switch(subject=None):
        subject = subject or 'privacy-' + uid()
        app.dependency_overrides[identity] = lambda: subject
        return client.get('/me').json()['id'], subject
    try:
        yield switch
    finally:
        app.dependency_overrides.pop(identity, None)


def start(client, question='A private thought'):
    result = client.post('/sessions', json={'event_id': uid(), 'problem_domain': 'math', 'problem_text': question, 'experience': 'chat'})
    assert result.status_code == 201, result.text
    return result.json()['id']


def test_opt_in_is_explicit_and_withdrawal_filters_research(client, accounts, monkeypatch):
    _, subject = accounts()
    monkeypatch.setenv('ADMIN_SUBJECTS', subject)
    before = client.get('/analytics/research?experience=chat').json()['session_count']
    sid = start(client)
    assert client.get('/privacy').json()['research_opt_in'] is False
    assert client.get('/analytics/research?experience=chat').json()['session_count'] == before
    assert client.post('/privacy', json={'research_opt_in': True, 'acknowledge_notice': True}).status_code == 200
    assert client.get('/analytics/research?experience=chat').json()['session_count'] == before + 1
    assert client.post('/privacy', json={'research_opt_in': False}).status_code == 200
    assert client.get('/analytics/research?experience=chat').json()['session_count'] == before
    assert client.get(f'/sessions/{sid}').status_code == 200


def test_export_and_operator_data_are_owner_scoped(client, accounts, monkeypatch):
    first, subject = accounts()
    sid = start(client, 'ONLY FIRST ACCOUNT')
    second, _ = accounts()
    start(client, 'ONLY SECOND ACCOUNT')
    export = client.get('/privacy/export')
    assert export.headers['cache-control'] == 'no-store'
    assert export.json()['account']['id'] == second
    assert 'ONLY FIRST ACCOUNT' not in export.text
    assert 'ONLY SECOND ACCOUNT' in export.text
    assert client.get(f'/sessions/{sid}').status_code == 404
    monkeypatch.setenv('AUTH_MODE', 'clerk')
    assert client.get('/operator/status').status_code == 403
    accounts(subject)
    monkeypatch.setenv('ADMIN_SUBJECTS', subject)
    assert client.get('/operator/status').status_code == 200


def test_hosted_notice_required_but_research_never_required(client, accounts, monkeypatch):
    accounts()
    monkeypatch.setenv('AUTH_MODE', 'clerk')
    payload = {'event_id': uid(), 'problem_domain': 'math', 'problem_text': 'Question'}
    assert client.post('/sessions', json=payload).status_code == 428
    assert client.post('/privacy', json={'research_opt_in': False, 'acknowledge_notice': True}).status_code == 200
    assert client.post('/sessions', json=payload).status_code == 201


def test_deletion_is_pending_idempotent_and_targeted(client, accounts):
    other_id, other_subject = accounts()
    other_sid = start(client, 'Other account survives')
    owner, subject = accounts()
    sid = start(client, 'Erase this conversation')
    client.post(f'/sessions/{sid}/title', json={'title': 'Private title'})
    client.post('/privacy', json={'research_opt_in': True})
    assert client.post('/privacy/deletion', json={'confirmation': 'delete'}).status_code == 422
    body = {'confirmation': 'DELETE MY CONVERSATIONS'}
    first = client.post('/privacy/deletion', json=body).json()
    request_id = first['deletion_request']['id']
    assert not first['research_opt_in']
    assert client.post('/privacy/deletion', json=body).json()['deletion_request']['id'] == request_id
    assert client.post('/privacy', json={'research_opt_in': True}).status_code == 409
    assert client.post('/sessions', json={'event_id': uid(), 'problem_domain': 'math', 'problem_text': 'Blocked'}).status_code == 409
    assert client.get(f'/sessions/{sid}').status_code == 200
    assert 'Erase this' in client.get('/privacy/export').text
    with pytest.raises(ValueError), engine.begin() as conn:
        fulfill(conn, request_id, other_id)
    with engine.begin() as conn:
        assert fulfill(conn, request_id, owner)
    assert client.get(f'/sessions/{sid}').status_code == 404
    assert client.get('/privacy').json()['last_erased_at']
    assert 'Erase this' not in client.get('/privacy/export').text
    # A replay must not erase new conversations created after completion.
    new_sid = start(client, 'A fresh start')
    with engine.begin() as conn:
        assert not fulfill(conn, request_id, owner)
    assert client.get(f'/sessions/{new_sid}').status_code == 200
    accounts(other_subject)
    assert client.get(f'/sessions/{other_sid}').status_code == 200
    for statement in ('DELETE FROM events WHERE session_id=:sid', 'UPDATE events SET event_type=event_type WHERE session_id=:sid'):
        with pytest.raises(DatabaseError), engine.begin() as conn:
            conn.execute(text(statement), {'sid': other_sid})


def test_erasure_rolls_back_trigger_and_keeps_usage(client, accounts):
    owner, _ = accounts()
    sid = start(client)
    request_id = client.post('/privacy/deletion', json={'confirmation': 'DELETE MY CONVERSATIONS'}).json()['deletion_request']['id']
    usage_id = uid()
    with SessionLocal() as db:
        db.add(AIUsageRequest(id=usage_id, user_id=owner, status='pending', attempt_budget=1, max_attempts=1,
            accounted_tokens=1, accounted_micro_usd=0, rate_micro_usd_per_million=0, created_at=now()))
        db.commit()
    with pytest.raises(ValueError), engine.begin() as conn:
        fulfill(conn, request_id, owner)
    with SessionLocal() as db:
        db.get(AIUsageRequest, usage_id).created_at = now() - timedelta(minutes=5)
        db.commit()
    with pytest.raises(RuntimeError), engine.begin() as conn:
        fulfill(conn, request_id, owner)
        raise RuntimeError('Synthetic failure after erasure, before commit')
    assert client.get(f'/sessions/{sid}').status_code == 200
    assert client.get('/privacy').json()['deletion_request']['status'] == 'pending'
    with pytest.raises(DatabaseError), engine.begin() as conn:
        conn.execute(text('DELETE FROM events WHERE session_id=:sid'), {'sid': sid})
    with engine.begin() as conn:
        fulfill(conn, request_id, owner)
    with SessionLocal() as db:
        assert db.get(AIUsageRequest, usage_id) is not None
        assert db.get(User, owner) is not None
        assert db.scalar(select(func.count()).select_from(Event).where(Event.user_id == owner)) == 0
