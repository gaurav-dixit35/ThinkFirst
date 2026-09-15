import asyncio
import json
import time
from uuid import uuid4

import httpx
import pytest
from apps.api import provider, routing


def configure(monkeypatch, names=('groq', 'gemini')):
    monkeypatch.setenv('AI_PROVIDER', names[0])
    monkeypatch.setenv('AI_FALLBACK_ORDER', ','.join(names))
    for name in names:
        monkeypatch.setenv(provider.PROVIDERS[name][1], 'synthetic-key')
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'test-account')


def transport(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))


def answer(name, text='Which constraint matters?'):
    if name == 'gemini':
        return {'modelVersion': 'actual-gemini', 'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': text}]}}]}
    return {'model': 'actual-model', 'choices': [{'finish_reason': 'stop', 'message': {'content': text}}]}


@pytest.mark.parametrize('failure', [401, 402, 403, 404, 429, 500, 503, 'network', 'malformed', 'tier', 'empty', 'truncated'])
def test_failover_from_real_adapter(monkeypatch, failure):
    configure(monkeypatch)
    calls, reports = [], []
    def handle(request):
        calls.append(request.url.host)
        if request.url.host == 'api.groq.com':
            if isinstance(failure, int):
                return httpx.Response(failure, headers={'retry-after': '30'}, json={'error': 'do not expose this'})
            if failure == 'network':
                raise httpx.ConnectError('secret synthetic transport details', request=request)
            if failure == 'malformed':
                return httpx.Response(200, text='{')
            body = answer('groq', 'The answer is 42.' if failure == 'tier' else '')
            if failure == 'truncated':
                body['choices'][0]['finish_reason'] = 'length'
            return httpx.Response(200, json=body)
        return httpx.Response(200, json=answer('gemini'))
    transport(monkeypatch, handle)
    result = routing.generate(1, 'A problem', '', [], on_attempt=reports.append)
    assert result.provider == 'gemini'
    assert calls == ['api.groq.com', 'generativelanguage.googleapis.com']
    assert [r['outcome'] for r in reports] == ['failed', 'success']
    assert 'secret' not in json.dumps(reports)


def test_timeout_cancels_before_trying_next_provider(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv('AI_PROVIDER_TIMEOUT_SECONDS', '1')
    cancelled = []
    async def generate(*args):
        if args[4] == 'groq':
            try:
                await asyncio.sleep(20)
            finally:
                cancelled.append(True)
        return provider.Generation('Which constraint matters?')
    monkeypatch.setattr(provider, 'generate_async', generate)
    began = time.monotonic()
    assert routing.generate(1, 'problem', '', []).provider == 'gemini'
    assert time.monotonic()-began < 3
    assert cancelled == [True]


def test_cooldown_and_credential_change(monkeypatch):
    configure(monkeypatch)
    calls = []
    async def generate(*args):
        calls.append(args[4])
        if args[4] == 'groq':
            raise provider.ProviderError('Check the API key', 'authentication')
        return provider.Generation('Which constraint matters?')
    monkeypatch.setattr(provider, 'generate_async', generate)
    for _ in range(2):
        routing.generate(1, 'problem', '', [])
    assert calls == ['groq', 'gemini', 'gemini']
    monkeypatch.setenv('GROQ_API_KEY', 'replacement-key')
    routing.generate(1, 'problem', '', [])
    assert calls[-2:] == ['groq', 'gemini']


def test_policy_refusal_does_not_shop_other_providers(monkeypatch):
    configure(monkeypatch)
    calls = []
    def handle(request):
        calls.append(request.url.host)
        return httpx.Response(200, json={'choices': [{'finish_reason': 'content_filter', 'message': {'content': ''}}]})
    transport(monkeypatch, handle)
    with pytest.raises(routing.Exhausted, match='rephrasing'):
        routing.generate(3, 'problem', '', [])
    assert calls == ['api.groq.com']


def test_all_providers_fail_and_disabled_fallback(monkeypatch):
    configure(monkeypatch)
    reports = []
    transport(monkeypatch, lambda r: httpx.Response(503))
    with pytest.raises(routing.Exhausted, match='saved'):
        routing.generate(1, 'problem', '', [], on_attempt=reports.append)
    assert len(reports) == 2
    routing.reset_cooldowns()
    monkeypatch.setenv('AI_FALLBACK_ENABLED', 'false')
    reports.clear()
    with pytest.raises(routing.Exhausted):
        routing.generate(1, 'problem', '', [], on_attempt=reports.append)
    assert len(reports) == 1


def test_cloudflare_needs_account_id_and_token(monkeypatch):
    monkeypatch.setenv('CLOUDFLARE_API_TOKEN', 'test')
    assert not provider.configuration('cloudflare')['configured']
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'test-account')
    assert provider.configuration('cloudflare')['configured']


def test_followup_preserves_bounded_history_through_fallback(monkeypatch):
    configure(monkeypatch, ('mistral', 'cloudflare'))
    contexts = []
    def handle(request):
        contexts.append(json.loads(json.loads(request.content)['messages'][1]['content']))
        if request.url.host == 'api.mistral.ai':
            return httpx.Response(429)
        assert '/accounts/test-account/ai/v1/chat/completions' in str(request.url)
        body = answer('cloudflare')
        body['choices'][0]['message']['content'] = [{'type': 'text', 'text': 'Subtract the same amount from both sides.'}]
        return httpx.Response(200, json=body)
    transport(monkeypatch, handle)
    history = [{'role': 'assistant', 'content': str(i)+'x'*3000} for i in range(20)]
    result = routing.generate(3, 'equation', 'subtract 3', ['one', 'two', 'three'], conversation=history, followup_text='Why subtract?')
    assert result.provider == 'cloudflare'
    assert contexts[0] == contexts[1]
    assert contexts[0]['followup_question'] == 'Why subtract?'
    assert sum(len(m['content']) for m in contexts[0]['conversation']) <= 24000
    assert contexts[0]['conversation'][-1] == history[-1]


def test_api_fallback_is_one_logical_request_and_followup_needs_new_evaluation(client, monkeypatch):
    configure(monkeypatch)
    calls, contexts = [], []
    def handle(request):
        calls.append(request.url.host)
        if request.url.host == 'api.groq.com':
            return httpx.Response(429)
        contexts.append(json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text']))
        return httpx.Response(200, json=answer('gemini'))
    transport(monkeypatch, handle)
    uid = lambda: str(uuid4())
    sid = client.post('/sessions', json={'event_id': uid(), 'problem_domain': 'math', 'problem_text': 'Solve an equation'}).json()['id']
    def emit(kind, payload):
        return client.post('/events', json={'event_id': uid(), 'session_id': sid, 'event_type': kind, 'payload': payload})
    assert emit('attempt_submitted', {'attempt_text': 'Subtract 3', 'is_partial': True}).status_code == 200
    for tier in (1, 2, 3):
        body = {'event_id': uid(), 'session_id': sid, 'tier': tier, 'provider': 'auto'}
        result = client.post('/ai/hint', json=body)
        assert result.status_code == 200, result.text
        assert result.json()['payload']['provider'] == 'gemini'
        assert client.post('/ai/hint', json=body).json()['id'] == result.json()['id']
        assert client.get('/ai/requests/'+body['event_id']).json()['status'] == 'delivered'
        assert emit('verification_skipped', {'hint_event_id': result.json()['id']}).status_code == 200
    assert emit('evaluation_submitted', {'makes_sense': True, 'reasoning': 'I checked it'}).status_code == 200
    followup = {**body, 'event_id': uid(), 'followup_text': 'Why subtract from both sides?'}
    result = client.post('/ai/hint', json=followup)
    assert result.status_code == 200, result.text
    assert contexts[-1]['followup_question'] == followup['followup_text']
    assert len(contexts[-1]['conversation']) == 3
    assert client.post('/ai/hint', json={**followup, 'followup_text': 'Different question'}).status_code == 409
    assert emit('verification_skipped', {'hint_event_id': result.json()['id']}).status_code == 200
    final = {'event_id': uid(), 'final_status': 'solved_with_ai'}
    assert client.post(f'/sessions/{sid}/close', json=final).status_code == 409
    data = client.get(f'/sessions/{sid}').json()
    assert data['summary']['ai_requests'] == 4
    assert data['summary']['ai_responses'] == 4
    assert not data['summary']['evaluation_completed']
    assert sum(e['event_type'] == 'ai_provider_attempted' for e in data['events']) == 8
    assert not any(e['event_type'] == 'ai_hint_failed' for e in data['events'])
    assert calls.count('api.groq.com') == 1
    assert emit('evaluation_submitted', {'makes_sense': True, 'reasoning': 'The follow-up explains it'}).status_code == 200
    assert client.post(f'/sessions/{sid}/close', json=final).status_code == 200


def test_request_polling_is_owner_scoped(client):
    from apps.api import main
    request_id = str(uuid4())
    with main.SessionLocal() as db:
        other = main.User(subject='poll-owner-'+request_id)
        db.add(other); db.flush()
        session = main.Session(user_id=other.id, problem_domain='math')
        db.add(session); db.flush()
        main.append(db, session, 'ai_hint_requested', {'tier_requested': 1}, request_id)
        db.commit()
    assert client.get('/ai/requests/'+request_id).status_code == 404


def test_total_deadline_is_shared_across_providers(monkeypatch):
    configure(monkeypatch, ('groq', 'gemini', 'mistral'))
    monkeypatch.setattr(routing, 'seconds', lambda name, *rest: 0.12 if name == 'AI_TOTAL_TIMEOUT_SECONDS' else 0.1)
    cancelled, reports = [], []
    async def generate(*args):
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.append(args[4])
    monkeypatch.setattr(provider, 'generate_async', generate)
    began = time.monotonic()
    with pytest.raises(routing.Exhausted):
        routing.generate(1, 'problem', '', [], on_attempt=reports.append)
    assert time.monotonic()-began < 0.5
    assert cancelled == ['groq', 'gemini']
    assert reports[-1]['error_code'] == 'deadline'


def test_all_failed_api_request_remains_retrievable_and_idempotent(client, monkeypatch):
    configure(monkeypatch)
    transport(monkeypatch, lambda request: httpx.Response(503))
    uid = lambda: str(uuid4())
    sid = client.post('/sessions', json={'event_id': uid(), 'problem_domain': 'math', 'problem_text': 'Synthetic failure QA'}).json()['id']
    client.post('/events', json={'event_id': uid(), 'session_id': sid, 'event_type': 'attempt_skipped', 'payload': {}})
    body = {'event_id': uid(), 'session_id': sid, 'tier': 1}
    assert client.post('/ai/hint', json=body).status_code == 502
    assert client.post('/ai/hint', json=body).status_code == 502
    status = client.get('/ai/requests/'+body['event_id']).json()
    assert status['status'] == 'failed'
    data = client.get(f'/sessions/{sid}').json()
    assert data['summary']['ai_requests'] == 1
    assert sum(e['event_type'] == 'ai_hint_failed' for e in data['events']) == 1
    assert sum(e['event_type'] == 'ai_provider_attempted' for e in data['events']) == 2
