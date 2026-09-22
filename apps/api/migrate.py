"""Run schema setup separately using an owner connection, never from HTTP routes."""
from .db import migrate, verify_schema


if __name__ == '__main__':
    try:
        migrate()
        verify_schema()
    except Exception as exc:
        print(f'Schema preparation failed ({type(exc).__name__}). Check the operator connection and database permissions; credentials are not printed.')
        raise SystemExit(1)
    print('Schema and event protection are ready.')
