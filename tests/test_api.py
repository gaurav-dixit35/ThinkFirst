from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from apps.api.db import engine
from apps.api import provider, routing

def eid(): return str(uuid4())
def start(client):
    response = client.post('/sessions', json={'event_id': eid(), 'problem_domain': 'math', 'problem_text': 'How can I compare two fractions?'})
    assert response.status_code == 201, response.text
    return response.json()['id']
def emit(client, sid, kind, payload, event_id=None):
    return client.post('/events', json={'event_id': event_id or eid(), 'session_id': sid, 'event_type': kind, 'payload': payload})
def close(client,sid,status): return client.post(f'/sessions/{sid}/close',json={'event_id':eid(),'final_status':status})

def test_full_flow_and_idempotency(client, monkeypatch):
    monkeypatch.setattr(routing, 'generate', lambda *args: provider.Generation('What common denominator could help you compare them?'))
    sid = start(client)
    attempt = emit(client,sid,'attempt_submitted',{'attempt_text':'I could use a common denominator.', 'is_partial':True})
    assert attempt.status_code == 200
    body = {'event_id':eid(),'session_id':sid,'tier':1}
    hint = client.post('/ai/hint',json=body)
    assert hint.status_code == 200, hint.text
    assert client.post('/ai/hint',json=body).json()['id'] == hint.json()['id']
    assert close(client,sid,'solved_with_ai').status_code == 409
    assert emit(client,sid,'verification_submitted',{'hint_event_id':hint.json()['id'],'matches_own_attempt':True,'justification':'It matches my common-denominator approach.'}).status_code == 200
    assert emit(client,sid,'evaluation_submitted',{'makes_sense':True,'reasoning':'Equivalent fractions preserve the quantities.'}).status_code == 200
    assert close(client,sid,'solved_with_ai').status_code == 200
    data=client.get(f'/sessions/{sid}').json()
    assert data['summary']['is_ai_first'] is False
    assert data['summary']['verification_rate'] == 1
    times=[e['created_at'] for e in data['events']]
    assert times == sorted(times)
    assert emit(client,sid,'attempt_skipped',{}).status_code == 409

def test_skip_ladder_and_unknown_events(client,monkeypatch):
    monkeypatch.setattr(routing,'generate',lambda *args:provider.Generation('What constraint matters here?'))
    sid=start(client)
    assert client.post('/ai/hint',json={'event_id':eid(),'session_id':sid,'tier':1}).status_code==409
    assert emit(client,sid,'attempt_skipped',{}).status_code==200
    assert client.post('/ai/hint',json={'event_id':eid(),'session_id':sid,'tier':3}).status_code==409
    hint=client.post('/ai/hint',json={'event_id':eid(),'session_id':sid,'tier':1}).json()
    assert emit(client,sid,'verification_skipped',{'hint_event_id':hint['id']}).status_code==200
    assert emit(client,sid,'evaluation_skipped',{}).status_code==200
    assert close(client,sid,'solved_independently').status_code==409
    assert close(client,sid,'solved_with_ai').status_code==200
    assert client.get(f'/sessions/{sid}').json()['summary']['is_ai_first'] is True
    sid=start(client)
    assert emit(client,sid,'made_up',{}).status_code==400
    assert emit(client,sid,'ai_hint_delivered',{}).status_code==400
    assert emit(client,sid,'attempt_submitted',{'attempt_text':'x','created_at':'2000-01-01'}).status_code==422
    assert emit(client,eid(),'attempt_skipped',{}).status_code==404

def test_duplicate_event_and_ownership(client):
    sid=start(client)
    event_id=eid()
    a=emit(client,sid,'attempt_submitted',{'attempt_text':'abc'},event_id)
    b=emit(client,sid,'attempt_submitted',{'attempt_text':'abc'},event_id)
    assert a.json()['id']==b.json()['id']
    assert emit(client,sid,'attempt_submitted',{'attempt_text':'different'},event_id).status_code==409
    from apps.api.main import app
    from apps.api.auth import identity
    app.dependency_overrides[identity]=lambda:'another-user'
    try:
        assert client.get(f'/sessions/{sid}').status_code==404
        assert emit(client,sid,'attempt_skipped',{}).status_code==404
    finally: app.dependency_overrides.clear()

def test_database_append_only(client):
    sid=start(client)
    for sql in ['UPDATE events SET event_type=event_type WHERE session_id=:sid','DELETE FROM events WHERE session_id=:sid']:
        with pytest.raises(DatabaseError):
            with engine.begin() as conn: conn.execute(text(sql),{'sid':sid})

def test_failure_and_violation_are_logged(client,monkeypatch):
    sid=start(client);emit(client,sid,'attempt_skipped',{})
    def fail(*args): raise provider.TierViolation('The answer is 42.')
    monkeypatch.setattr(routing,'generate',fail)
    assert client.post('/ai/hint',json={'event_id':eid(),'session_id':sid,'tier':1}).status_code==502
    types=[e['event_type'] for e in client.get(f'/sessions/{sid}').json()['events']]
    assert 'hint_tier_violation' in types and 'ai_hint_failed' in types
    assert 'ai_hint_delivered' not in types
    assert close(client,sid,'abandoned').status_code==200

def test_admin_and_invalidation(client,monkeypatch):
    assert client.get('/analytics/research').status_code==403
    sid=start(client)
    a=emit(client,sid,'attempt_submitted',{'attempt_text':'bad input'}).json()
    assert emit(client,sid,'event_invalidated',{'target_event_id':a['id'],'reason':'correction'}).status_code==403
    monkeypatch.setenv('ADMIN_SUBJECTS','local-development-participant')
    assert emit(client,sid,'event_invalidated',{'target_event_id':a['id'],'reason':'correction'}).status_code==200
    assert not any(e['id']==a['id'] for e in client.get(f'/sessions/{sid}').json()['events'])
    assert client.get('/analytics/research').status_code==200

def test_all_tiers_require_explicit_requests_and_checks(client,monkeypatch):
    monkeypatch.setattr(routing,'generate',lambda *args:provider.Generation('What constraint matters here?'))
    sid=start(client)
    emit(client,sid,'attempt_skipped',{})
    for tier in (1,2,3):
        hint=client.post('/ai/hint',json={'event_id':eid(),'session_id':sid,'tier':tier})
        assert hint.status_code==200, hint.text
        if tier<3:
            assert client.post('/ai/hint',json={'event_id':eid(),'session_id':sid,'tier':tier+1}).status_code==409
        assert emit(client,sid,'verification_skipped',{'hint_event_id':hint.json()['id']}).status_code==200
    emit(client,sid,'evaluation_skipped',{})
    assert close(client,sid,'solved_with_ai').status_code==200
    data=client.get(f'/sessions/{sid}').json()
    assert data['summary']['ai_requests']==3
    assert data['summary']['verification_rate']==0


def test_concurrent_duplicate_request_persists_once(client):
    if engine.dialect.name!='postgresql': pytest.skip('PostgreSQL row-lock concurrency test')
    from concurrent.futures import ThreadPoolExecutor
    sid=start(client); event_id=eid()
    def send(): return emit(client,sid,'attempt_submitted',{'attempt_text':'Concurrent retry'},event_id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:send(),range(2)))
    assert [r.status_code for r in results]==[200,200]
    events=client.get(f'/sessions/{sid}').json()['events']
    assert sum(e['id']==event_id for e in events)==1


def test_ai_setup_status_never_exposes_credentials(client,monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY',raising=False)
    assert client.get('/ai/status').json()['configured'] is False
    monkeypatch.setenv('ANTHROPIC_API_KEY','test-secret')
    response=client.get('/ai/status')
    assert response.json()['configured'] is True
    assert 'test-secret' not in response.text


def test_can_finish_after_ai_failed_without_claiming_zero_requests(client,monkeypatch):
    sid=start(client)
    emit(client,sid,'attempt_submitted',{'attempt_text':'I can work this out myself.'})
    def fail(*args): raise ValueError('Provider unavailable')
    monkeypatch.setattr(routing,'generate',fail)
    assert client.post('/ai/hint',json={'event_id':eid(),'session_id':sid,'tier':1}).status_code==502
    assert close(client,sid,'solved_without_ai_response').status_code==200
    summary=client.get(f'/sessions/{sid}').json()['summary']
    assert summary['ai_requests']==1
    assert summary['ai_responses']==0
    assert summary['no_ai_completion'] is False


def test_retry_recovers_an_expired_request_id(client,monkeypatch):
    from datetime import timedelta
    from apps.api import main
    from apps.api.db import SessionLocal, Session
    sid=start(client);emit(client,sid,'attempt_skipped',{})
    request_id=eid()
    with SessionLocal() as db:
        s=db.get(Session,sid)
        main.append(db,s,'ai_hint_requested',{'tier_requested':1,'preceded_by_attempt':False,'time_since_session_start_ms':0},request_id)
        db.commit()
    later=main.now()+timedelta(seconds=120)
    monkeypatch.setattr(main,'now',lambda:later)
    response=client.post('/ai/hint',json={'event_id':request_id,'session_id':sid,'tier':1})
    assert response.status_code==502
    assert 'interrupted' in response.json()['detail']
    monkeypatch.setattr(routing,'generate',lambda *args:provider.Generation('Which constraint matters?'))
    assert client.post('/ai/hint',json={'event_id':eid(),'session_id':sid,'tier':1}).status_code==200


def test_provider_selection_and_model_are_recorded(client,monkeypatch):
    calls=[]
    def generate(*args):
        calls.append(args[4])
        return provider.Generation('Which constraint matters?', 'actual-model')
    monkeypatch.setattr(routing,'generate',generate)
    sid=start(client);emit(client,sid,'attempt_skipped',{})
    body={'event_id':eid(),'session_id':sid,'tier':1,'provider':'groq'}
    response=client.post('/ai/hint',json=body)
    assert response.status_code==200
    assert response.json()['payload']['provider']=='groq'
    assert response.json()['payload']['reported_model']=='actual-model'
    assert client.post('/ai/hint',json={**body,'provider':'gemini'}).status_code==409
    assert calls==['groq']
    request=next(e for e in client.get(f'/sessions/{sid}').json()['events'] if e['event_type']=='ai_hint_requested')
    assert request['payload']['provider']=='groq'


def test_all_provider_statuses_expose_presence_only(client,monkeypatch):
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'test-account')
    for name,(_,key,_,_) in provider.PROVIDERS.items(): monkeypatch.setenv(key,'secret-'+name)
    response=client.get('/ai/status')
    assert {p['id'] for p in response.json()['providers']}==set(provider.PROVIDERS)
    assert all(p['configured'] for p in response.json()['providers'])
    assert 'secret-' not in response.text


@pytest.mark.parametrize('tier,text_value',[(1,'The answer is 4.'),(1,'a '*36+'?'),(2,'```python\nprint(1)\n```'),(2,'word '*41)])
def test_tier_guard(tier,text_value):
    with pytest.raises(provider.TierViolation): provider.validate_tier(tier,text_value)

