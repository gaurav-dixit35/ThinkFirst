"""Budget safety checks use synthetic responses and isolated participants only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import json

import httpx
import pytest
from fastapi import HTTPException
from apps.api import provider, usage
from apps.api.auth import identity
from apps.api.db import AIUsageRequest, SessionLocal
from apps.api.main import app


@pytest.fixture
def participant(client):
    subject = 'budget-test-' + str(uuid4())
    app.dependency_overrides[identity] = lambda: subject
    try:
        yield client.get('/me').json()['id']
    finally:
        app.dependency_overrides.pop(identity, None)


def start(client):
    return client.post('/sessions', json=dict(event_id=str(uuid4()), problem_domain='math',
        problem_text='Solve 2x + 3 = 11', experience='chat')).json()['id']


def request(sid, **extra):
    return dict(event_id=str(uuid4()), session_id=sid, tier=3, **extra)


def synthetic(monkeypatch, handle):
    monkeypatch.setenv('AI_PROVIDER', 'groq')
    monkeypatch.setenv('AI_FALLBACK_ORDER', 'groq,gemini')
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic')
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic')
    client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs))


def response(text='The answer is 4.', finish='stop'):
    return {'choices': [{'finish_reason': finish, 'message': {'content': text}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30,
                      'completion_tokens_details': {'reasoning_tokens': 5}}}


def test_daily_allowance_idempotency_and_self_thinking(client, participant, monkeypatch):
    calls = []
    synthetic(monkeypatch, lambda r: calls.append(r) or httpx.Response(200, json=response()))
    monkeypatch.setenv('AI_USER_DAILY_REQUESTS', '1')
    sid = start(client)
    body = request(sid, answer_style='detailed')
    first = client.post('/ai/hint', json=body)
    assert first.status_code == 200, first.text
    assert client.post('/ai/hint', json=body).json()['id'] == first.json()['id']
    assert client.post('/ai/hint', json={**body, 'answer_style': 'concise'}).status_code == 409
    rejected = client.post('/ai/hint', json=request(sid, followup_text='Why?'))
    assert rejected.status_code == 429
    assert len(calls) == 1
    assert client.get('/ai/usage').json()['requests_remaining'] == 0
    assert client.post('/events', json=dict(event_id=str(uuid4()), session_id=sid,
        event_type='attempt_submitted', payload={'attempt_text': 'Check by substituting 4.'})).status_code == 200
    assert client.get('/sessions/'+sid).json()['summary']['ai_requests'] == 1
    with SessionLocal() as db:
        row = db.get(AIUsageRequest, body['event_id'])
        assert row.accounted_tokens == 30 and row.status == 'finished'


def test_failed_generation_usage_is_retained_through_fallback(client, participant, monkeypatch):
    def handle(r):
        if r.url.host == 'api.groq.com':
            return httpx.Response(200, json=response('incomplete', 'length'))
        return httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'The answer is 4.'}]}}],
            'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':15,'thoughtsTokenCount':5,'totalTokenCount':30}})
    synthetic(monkeypatch, handle)
    body = request(start(client))
    assert client.post('/ai/hint', json=body).status_code == 200
    with SessionLocal() as db:
        row = db.get(AIUsageRequest, body['event_id'])
        assert row.accounted_tokens == 60
        assert [a['outcome'] for a in row.attempts] == ['failed', 'success']
        assert row.attempts[0]['usage']['reasoning_tokens'] == 5


def test_unknown_failure_keeps_reservation_and_attempts_are_bounded(client, participant, monkeypatch):
    calls = []
    synthetic(monkeypatch, lambda r: calls.append(r) or httpx.Response(503))
    monkeypatch.setenv('AI_MAX_PROVIDER_ATTEMPTS', '1')
    body = request(start(client))
    assert client.post('/ai/hint', json=body).status_code == 502
    with SessionLocal() as db:
        row = db.get(AIUsageRequest, body['event_id'])
        assert row.accounted_tokens == row.attempt_budget
        assert row.attempts[0]['usage'] is None
    assert len(calls) == 1


def test_global_money_and_token_caps_reject_before_network(client, participant, monkeypatch):
    calls = []
    synthetic(monkeypatch, lambda r: calls.append(r) or httpx.Response(200, json=response()))
    sid = start(client)
    monkeypatch.setenv('AI_GLOBAL_DAILY_BUDGET_USD', '0.000001')
    monkeypatch.setenv('AI_MAX_USD_PER_MILLION_TOKENS', '100')
    assert client.post('/ai/hint', json=request(sid)).status_code == 429
    monkeypatch.setenv('AI_GLOBAL_DAILY_BUDGET_USD', '0')
    monkeypatch.setenv('AI_GLOBAL_DAILY_TOKENS', '1')
    assert client.post('/ai/hint', json=request(sid)).status_code == 429
    assert not calls
    assert client.get('/ai/usage').json()['requests_used'] == 0


def test_atomic_admission_across_workers(client, participant, monkeypatch):
    monkeypatch.setenv('AI_USER_DAILY_REQUESTS', '1')
    gate = Barrier(2)
    def admit():
        with SessionLocal() as db:
            gate.wait(timeout=5)
            try:
                usage.reserve(db, str(uuid4()), participant, 100, 1)
                db.commit()
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(admit) for _ in range(2)]
        assert sorted(f.result(timeout=10) for f in futures) == [200, 429]


def test_concurrency_rate_and_expired_reservations(client, participant, monkeypatch):
    monkeypatch.setenv('AI_USER_CONCURRENCY', '1')
    with SessionLocal() as db:
        first = str(uuid4())
        usage.reserve(db, first, participant, 100, 2)
        db.commit()
        with pytest.raises(HTTPException, match='pending'):
            usage.reserve(db, str(uuid4()), participant, 100, 2)
        db.rollback()
        row = db.get(AIUsageRequest, first)
        row.created_at = usage.now()-usage.timedelta(seconds=100)
        db.commit()
        # Expiry releases concurrency, but keeps the entire unknown spending envelope.
        usage.reserve(db, str(uuid4()), participant, 100, 2)
        db.commit()
        assert db.get(AIUsageRequest, first).accounted_tokens == 200
        monkeypatch.setenv('AI_USER_REQUESTS_PER_MINUTE', '1')
        with pytest.raises(HTTPException, match='minute'):
            usage.reserve(db, str(uuid4()), participant, 100, 2)


def test_accounting_normalizes_reasoning_cache_and_reported_cost():
    normalized = provider.response_usage('openrouter', {**response(), 'usage':{**response()['usage'],'cost':0.001}})
    assert normalized['total_tokens'] == 30 and normalized['cost_micro_usd'] == 1000
    assert provider.response_usage('groq', {}) is None
    anthropic = provider.response_usage('anthropic', {'usage':{'input_tokens':10,'output_tokens':20,
        'cache_read_input_tokens':100,'cache_creation_input_tokens':50}})
    assert anthropic['total_tokens'] == 180
    assert provider.response_usage('gemini', {'usageMetadata':{'totalTokenCount':50}})['total_tokens'] == 50


def test_dollar_budget_requires_rate_and_invalid_limits_fail_closed(monkeypatch):
    monkeypatch.setenv('AI_GLOBAL_DAILY_BUDGET_USD', '1')
    with pytest.raises(ValueError, match='requires'):
        usage.limits()
    monkeypatch.setenv('AI_GLOBAL_DAILY_BUDGET_USD', 'NaN')
    with pytest.raises(ValueError, match='non-negative'):
        usage.limits()


def test_concise_detailed_reach_provider_and_have_distinct_budgets(client, participant, monkeypatch):
    sent = []
    synthetic(monkeypatch, lambda r: sent.append(json.loads(r.content)) or httpx.Response(200,json=response()))
    sid = start(client)
    assert client.post('/ai/hint', json=request(sid, answer_style='concise')).status_code == 200
    assert client.post('/ai/hint', json=request(sid, answer_style='detailed', followup_text='Explain the steps')).status_code == 200
    assert sent[0]['max_completion_tokens'] < sent[1]['max_completion_tokens']
    assert 'Explain in detail' in sent[1]['messages'][0]['content']


def test_operator_usage_is_not_exposed_to_hosted_participants(client, participant, monkeypatch):
    from apps.api import main
    monkeypatch.setattr(main, 'mode', lambda:'clerk')
    monkeypatch.setenv('ADMIN_SUBJECTS', '')
    assert 'workspace' not in client.get('/ai/usage').json()
