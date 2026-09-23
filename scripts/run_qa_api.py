"""Run isolated synthetic browser APIs without exposing local credentials."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port',type=int,choices=(8001,8002),required=True)
args=parser.parse_args()
url=make_url(dotenv_values(ROOT/'.env',interpolate=False)['DATABASE_URL'])
if url.get_backend_name()!='postgresql' or url.host not in ('localhost','127.0.0.1'):
    raise SystemExit('Browser QA requires the local PostgreSQL installation.')
env={**os.environ,'DATABASE_URL':url.set(host='127.0.0.1',database='thinkfirst_test').render_as_string(hide_password=False),
     'WEB_ORIGINS':'http://localhost:3000,http://localhost:3100','QA_MOCK_AI':'true' if args.port==8002 else 'false',
     'AI_USER_DAILY_REQUESTS':'1000000','AI_USER_REQUESTS_PER_MINUTE':'1000000',
     'AI_GLOBAL_DAILY_TOKENS':'1000000000','AI_GLOBAL_DAILY_BUDGET_USD':'0'}
raise SystemExit(subprocess.call([sys.executable,'-m','uvicorn','tests.browser_api:app','--host','127.0.0.1','--port',str(args.port),'--no-access-log'],cwd=ROOT,env=env))
