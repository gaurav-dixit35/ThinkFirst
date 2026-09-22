"""Binary-safe PostgreSQL backups and restore drills into NEW databases only.

Uses installed pg_dump/pg_restore/createdb, or --container for the local Docker database.
Credentials come from DATABASE_URL; no URL/password is printed or put in process arguments.
"""
import argparse
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4
from .deployment import database_url
from dotenv import load_dotenv


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup', 'restore-drill'])
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--container', help='Local PostgreSQL Docker container; uses its POSTGRES_USER.')
    parser.add_argument('--database', help='NEW restore target, must start with thinkfirst_restore_')
    args = parser.parse_args()
    url = database_url(os.environ['DATABASE_URL'])
    if url.get_backend_name() != 'postgresql':
        parser.error('PostgreSQL DATABASE_URL required.')
    target = args.database
    if args.action == 'restore-drill' and (not target or not re.fullmatch(r'thinkfirst_restore_[a-z0-9_]+', target) or target == url.database):
        parser.error('Choose a new thinkfirst_restore_... database; the source database is never a restore target.')
    env = dict(os.environ, PGHOST=url.host or 'localhost', PGPORT=str(url.port or 5432), PGUSER=url.username or '', PGPASSWORD=url.password or '', PGDATABASE=url.database or '')
    for key, value in url.query.items():
        if key in ('sslmode', 'sslrootcert', 'sslcert', 'sslkey'):
            env['PG' + key.upper()] = str(value)

    def run(command, **kwargs):
        # Capture diagnostics: connection errors can contain host/account details.
        result = subprocess.run(command, env=env, stderr=subprocess.PIPE, **kwargs)
        if result.returncode:
            raise RuntimeError(f'{command[0]} failed with exit code {result.returncode}. Check database access and PostgreSQL tool versions; no source data was replaced.')

    def pg(tool, *arguments):
        if args.container:
            # No shell interpolation; local Docker defaults match compose.yaml.
            return ['docker', 'exec', args.container, tool, '-U', url.username or 'thinkfirst', *arguments]
        return [tool, *arguments]

    file = args.file.resolve()
    if args.action == 'backup':
        file.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive create avoids clobbering an existing backup. pg_dump writes binary bytes.
        try:
            with file.open('xb') as output:
                run(pg('pg_dump', '-Fc', '-d', url.database or 'thinkfirst'), stdout=output)
        except Exception:
            # A failed dump is never advertised as recoverable. Keep partial files for diagnosis.
            raise
        print(f'Backup created: {file}. Encrypt it and verify a restore before relying on it.')
    else:
        if not file.is_file():
            parser.error('Backup file does not exist.')
        # createdb intentionally fails when the target already exists. Never use --clean.
        run(pg('createdb', target), stdout=subprocess.PIPE)
        if args.container:
            remote = f'/tmp/thinkfirst-restore-{uuid4().hex}.dump'
            run(['docker', 'cp', str(file), f'{args.container}:{remote}'], stdout=subprocess.PIPE)
            try:
                run(pg('pg_restore', '--exit-on-error', '--single-transaction', '--no-owner', '--no-privileges', '-d', target, remote), stdout=subprocess.PIPE)
            finally:
                run(['docker', 'exec', args.container, 'rm', '--', remote], stdout=subprocess.PIPE)
        else:
            run(pg('pg_restore', '--exit-on-error', '--single-transaction', '--no-owner', '--no-privileges', '-d', target, str(file)), stdout=subprocess.PIPE)
        print(f'Restored into new database {target}. Verify account counts, event triggers and /health before any cutover. The source was unchanged.')


if __name__ == '__main__':
    main()
