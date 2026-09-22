"""Deployment configuration checks. Never return environment values or secrets."""
import os
import re
from sqlalchemy.engine import make_url


def database_url(value):
    try:
        url = make_url(value)
    except Exception:
        raise ValueError('DATABASE_URL is invalid; check its format in your secret store.') from None
    if url.drivername in ('postgres', 'postgresql'):
        url = url.set(drivername='postgresql+psycopg')
    return url


def auto_migrate():
    default = 'true' if os.getenv('ENVIRONMENT', 'production') == 'development' else 'false'
    value = os.getenv('AUTO_MIGRATE', default).lower()
    if value not in ('true', 'false'):
        raise ValueError('AUTO_MIGRATE must be true or false.')
    if value == 'true' and os.getenv('ENVIRONMENT', 'production') != 'development':
        raise ValueError('Run migrations separately before starting the production API.')
    return value == 'true'


def public_info():
    email = os.getenv('SUPPORT_EMAIL', '').strip()
    if email and (len(email) > 254 or not re.fullmatch(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', email)):
        raise ValueError('SUPPORT_EMAIL must be a valid contact email address.')
    return {'operator': os.getenv('OPERATOR_NAME', '').strip()[:120] or None,
            'support_email': email or None}


def readiness(check_database=False):
    from .auth import validate_configuration
    from . import provider, routing, usage
    issues = []
    def check(condition, message):
        if not condition: issues.append(message)
    check(os.getenv('ENVIRONMENT') == 'production', 'Set ENVIRONMENT=production for the hosted API.')
    check(os.getenv('AUTH_MODE') == 'clerk', 'Set AUTH_MODE=clerk for separate signed-in accounts.')
    try:
        validate_configuration()
    except (ValueError, RuntimeError):
        issues.append('Correct CLERK_ISSUER and exact HTTPS WEB_ORIGINS.')
    try:
        check(not auto_migrate(), 'Disable automatic migrations before a production release.')
    except ValueError:
        issues.append('Set AUTO_MIGRATE=false; apply migrations with the operator command.')
    try:
        url = database_url(os.getenv('DATABASE_URL', ''))
        check(url.get_backend_name() == 'postgresql' and bool(url.host and url.database and url.username and url.password), 'Set a complete PostgreSQL DATABASE_URL.')
        check(url.password not in ('thinkfirst', 'password', 'postgres'), 'Replace the development/default database password.')
    except Exception:
        issues.append('Set a valid PostgreSQL DATABASE_URL.')
    try:
        info = public_info()
        check(bool(info['operator']), 'Set OPERATOR_NAME for the public data notice.')
        check(bool(info['support_email']), 'Set SUPPORT_EMAIL for support and data requests.')
    except ValueError:
        issues.append('Correct SUPPORT_EMAIL.')
    check(bool(os.getenv('ADMIN_SUBJECTS', '').strip()), 'Set ADMIN_SUBJECTS to the pilot operator Clerk subject.')
    try:
        check(any(provider.configuration(p)['configured'] for p in routing.order()), 'Configure at least one usable provider key/account setting.')
        limits = usage.limits()
        check(bool(limits['budget_micro_usd']), 'Configure AI_GLOBAL_DAILY_BUDGET_USD and its token-price ceiling before public use.')
        if provider.configuration('openrouter')['configured']:
            check(provider.configuration('openrouter')['model'] != 'openrouter/auto', 'Choose a fixed OPENROUTER_MODEL with a known price ceiling before public use.')
    except (ValueError, RuntimeError):
        issues.append('Correct AI routing, allowance, or pricing configuration.')
    if check_database:
        try:
            from .db import engine, verify_schema
            from .permissions import verify_runtime
            verify_schema()
            with engine.connect() as connection:
                verify_runtime(connection)
        except Exception:
            issues.append('Database readiness failed: check connectivity, migrated schema, immutable events and restricted runtime permissions.')
    return issues


if __name__ == '__main__':
    from dotenv import load_dotenv
    import argparse
    load_dotenv()
    parser = argparse.ArgumentParser(description='Read-only launch checks; never calls AI providers or prints credentials.')
    parser.add_argument('--database', action='store_true', help='Also connect to verify schema and restricted runtime privileges.')
    args = parser.parse_args()
    try:
        problems = readiness(args.database)
    except Exception:
        problems = ['Configuration could not be loaded. Check database and AI environment settings; no secret values are printed.']
    for problem in problems:
        print('ACTION: ' + problem)
    print('Configuration needs attention.' if problems else 'API configuration checks passed. Credentials, infrastructure and live behavior still need verification.')
    raise SystemExit(1 if problems else 0)
