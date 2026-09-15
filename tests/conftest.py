import os
import tempfile
from pathlib import Path
os.environ['DATABASE_URL'] = os.getenv('TEST_DATABASE_URL', 'sqlite:///' + str(Path(tempfile.gettempdir()) / ('thinkfirst-test-' + str(os.getpid()) + '.db')).replace('\\', '/'))
os.environ['AUTH_MODE'] = 'development'
os.environ['ENVIRONMENT'] = 'development'
os.environ['AI_PROVIDER'] = 'anthropic'  # Legacy fixture; provider adapter tests select each service explicitly.

import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

@pytest.fixture(autouse=True)
def isolated_ai(monkeypatch):
    from apps.api import provider, routing
    for _, key, _, _ in provider.PROVIDERS.values():
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv('CLOUDFLARE_API_KEY', raising=False)
    monkeypatch.delenv('CLOUDFLARE_ACCOUNT_ID', raising=False)
    monkeypatch.setenv('AI_PROVIDER', 'anthropic')
    monkeypatch.setenv('AI_FALLBACK_ENABLED', 'true')
    monkeypatch.setenv('AI_FALLBACK_ORDER', routing.DEFAULT_ORDER)
    routing.reset_cooldowns()

@pytest.fixture
def client():
    with TestClient(app) as test:
        yield test
