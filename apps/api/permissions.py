"""Operator-only grants; production startup verifies the runtime role is limited.

Create a separate PostgreSQL login through the database administrator first.
Run with the owner DATABASE_URL and RUNTIME_DATABASE_ROLE set to that login name.
No passwords are accepted on command lines or printed.
"""
import os
from sqlalchemy import text
from .db import Base, engine


def verify_runtime(conn, role=None, require_access=True):
    role = role or conn.exec_driver_sql('SELECT current_user').scalar_one()
    record = conn.execute(text('SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname=:role'), {'role': role}).one_or_none()
    if record is None or any(record):
        raise RuntimeError('Use a restricted PostgreSQL login for the running API.')
    unsafe = conn.execute(text("""SELECT
      pg_has_role(:role, datdba, 'MEMBER') OR
      has_database_privilege(:role, current_database(), 'CREATE') OR
      has_schema_privilege(:role, 'public', 'CREATE')
      FROM pg_database WHERE datname=current_database()"""), {'role': role}).scalar_one()
    for table in Base.metadata.sorted_tables:
        owned = conn.execute(text("SELECT pg_has_role(:role, relowner, 'MEMBER') FROM pg_class WHERE oid=to_regclass(:table)"), {'role': role, 'table': 'public.' + table.name}).scalar()
        if owned or conn.execute(text("SELECT has_table_privilege(:role, :table, 'TRUNCATE')"), {'role': role, 'table': 'public.' + table.name}).scalar():
            unsafe = True
    if unsafe:
        raise RuntimeError('The API database login has owner, DDL or truncate access. Use the restricted runtime role.')
    if conn.execute(text("SELECT has_table_privilege(:role, 'public.events', 'UPDATE,DELETE,TRIGGER')"), {'role': role}).scalar():
        raise RuntimeError('The API database login can modify event history. Remove these permissions.')
    if require_access:
        if not conn.execute(text("SELECT has_schema_privilege(:role, 'public', 'USAGE')"), {'role': role}).scalar():
            raise RuntimeError('The API database login needs schema usage; run the runtime grant command.')
        for table in Base.metadata.sorted_tables:
            for privilege in ('SELECT', 'INSERT') if table.name == 'events' else ('SELECT', 'INSERT', 'UPDATE'):
                allowed = conn.execute(text('SELECT has_table_privilege(:role, :table, :privilege)'), {'role': role, 'table': 'public.' + table.name, 'privilege': privilege}).scalar()
                if not allowed:
                    raise RuntimeError('The API database login is missing application permissions; run the runtime grant command.')


def grant_runtime(role, target=engine):
    if target.dialect.name != 'postgresql':
        raise ValueError('Runtime grants require PostgreSQL.')
    if not role or len(role.encode('utf-8')) > 63:
        raise ValueError('Set RUNTIME_DATABASE_ROLE to the existing separate API login.')
    quote = target.dialect.identifier_preparer.quote_identifier
    with target.begin() as conn:
        verify_runtime(conn, role, require_access=False)  # Refuse owner/admin identities before changing anything.
        conn.exec_driver_sql(f'GRANT CONNECT ON DATABASE {quote(conn.exec_driver_sql("SELECT current_database()").scalar_one())} TO {quote(role)}')
        conn.exec_driver_sql(f'GRANT USAGE ON SCHEMA public TO {quote(role)}')
        for table in Base.metadata.sorted_tables:
            privilege = 'SELECT, INSERT' if table.name == 'events' else 'SELECT, INSERT, UPDATE'
            conn.exec_driver_sql(f'GRANT {privilege} ON TABLE public.{quote(table.name)} TO {quote(role)}')
        verify_runtime(conn, role)


if __name__ == '__main__':
    try:
        grant_runtime(os.getenv('RUNTIME_DATABASE_ROLE', ''))
    except Exception as exc:
        print(f'Runtime grants failed ({type(exc).__name__}). Check the separate role, schema and owner access. No credentials are printed.')
        raise SystemExit(1)
    print('Runtime grants applied. Use that login only in the API DATABASE_URL; keep the owner login offline.')
