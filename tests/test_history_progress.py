from uuid import uuid4
import json
from datetime import timedelta
import pytest
import httpx
from apps.api import activity, provider, routing
from apps.api.auth import identity
from apps.api.db import Event, Session, SessionLocal, AIUsageRequest, now
from apps.api.main import app


REAL_GENERATE=routing.generate

def uid():return str(uuid4())


@pytest.fixture
def learner(client,monkeypatch):
    subject='history-'+uid()
    app.dependency_overrides[identity]=lambda:subject
    calls=[]
    monkeypatch.setattr(routing,'generate',lambda *args:calls.append(args) or provider.Generation('A visible explanation.'))
    try:yield {'id':client.get('/me').json()['id'],'subject':subject,'calls':calls}
    finally:app.dependency_overrides.pop(identity,None)


def start(client,text='Explain a loop',experience='chat'):
    response=client.post('/sessions',json=dict(event_id=uid(),problem_domain='coding',problem_text=text,experience=experience))
    assert response.status_code==201,response.text
    return response.json()['id']


def emit(client,sid,kind,payload):
    response=client.post('/events',json=dict(event_id=uid(),session_id=sid,event_type=kind,payload=payload))
    assert response.status_code==200,response.text
    return response.json()


def answer(client,sid,followup=None):
    body=dict(event_id=uid(),session_id=sid,tier=3)
    if followup:body['followup_text']=followup
    response=client.post('/ai/hint',json=body)
    assert response.status_code==200,response.text
    return response.json()


def review(client,sid,eid=None):
    return client.post(f'/sessions/{sid}/analysis',json=dict(event_id=eid or uid(),session_id=sid))


def test_history_search_titles_text_literal_wildcards_and_invalidations(client,learner,monkeypatch):
    sid=start(client,'Original question')
    attempt=emit(client,sid,'attempt_submitted',{'attempt_text':'Distinctive saved thinking'})
    answer(client,sid)
    answer(client,sid,'A follow-up about turtles')
    for query in ('Original','distinctive','visible explanation','turtles'):
        response=client.get('/history',params={'q':query})
        assert response.status_code==200,response.text
        assert response.json()['total']==1
    assert client.post(f'/sessions/{sid}/title',json={'title':'50%_complete'}).status_code==200
    assert client.get('/history',params={'q':'%_'}).json()['items'][0]['title']=='50%_complete'
    assert client.get('/history',params={'q':'50ZZcomplete'}).json()['total']==0
    assert client.get('/history',params={'q':'Original'}).json()['total']==1
    monkeypatch.setenv('ADMIN_SUBJECTS',learner['subject'])
    emit(client,sid,'event_invalidated',{'target_event_id':attempt['id'],'reason':'Synthetic correction'})
    assert client.get('/history',params={'q':'Distinctive'}).json()['total']==0
    assert client.post(f'/sessions/{sid}/title',json={'title':None}).status_code==200
    assert client.get('/sessions/'+sid).json()['title']=='Original question'
    assert client.post(f'/sessions/{sid}/title',json={'title':'   '}).status_code==422


def test_history_paginates_past_old_100_limit(client,learner):
    # Seed only the isolated test DB; no model calls or research records in main DB.
    with SessionLocal() as db:
        for i in range(110):
            session=Session(user_id=learner['id'],problem_domain='math',started_at=now()-timedelta(minutes=i))
            db.add(session);db.flush()
            db.add(Event(user_id=learner['id'],session_id=session.id,event_type='session_started',
                         payload={'problem_text':f'Archive item {i}','problem_domain':'math','experience':'chat'}))
        db.commit()
    page=client.get('/history?offset=100&limit=25').json()
    assert page['total']==110 and len(page['items'])==10 and not page['has_more']
    assert client.get('/history',params={'q':'Archive item 109'}).json()['total']==1
    assert client.get('/history?limit=999').status_code==422
    assert client.get('/history?offset=-1').status_code==422
    assert not learner['calls']


def test_status_protocol_and_owner_filters_and_rename_closed(client,learner):
    completed=start(client,'Finished work')
    emit(client,completed,'attempt_submitted',{'attempt_text':'My answer'})
    client.post(f'/sessions/{completed}/close',json={'event_id':uid(),'final_status':'solved_independently'})
    abandoned=start(client,'Unfinished work')
    client.post(f'/sessions/{abandoned}/close',json={'event_id':uid(),'final_status':'abandoned'})
    start(client,'Study record','guided')
    assert client.get('/history?status=completed').json()['items'][0]['status_label']=='Completed independently'
    assert client.get('/history?status=abandoned').json()['items'][0]['status_label']=='Left unfinished'
    assert client.get('/history?experience=guided').json()['total']==1
    assert client.post(f'/sessions/{completed}/title',json={'title':'My completed work'}).status_code==200
    assert client.get('/sessions/'+completed).json()['status']=='closed'
    app.dependency_overrides[identity]=lambda:'different-history-user'
    assert client.get('/history').json()['total']==0
    assert client.post(f'/sessions/{completed}/title',json={'title':'Intrusion'}).status_code==404
    assert client.get('/progress').json()['totals']['conversations']==0


def test_progress_is_mode_aware_and_separates_guided_and_reviews(client,learner):
    own=start(client)
    emit(client,own,'attempt_submitted',{'attempt_text':'An idea'})
    both=start(client)
    emit(client,both,'attempt_submitted',{'attempt_text':'My first thought'})
    answer(client,both)
    assert review(client,both).status_code==200
    ai=start(client);answer(client,ai)
    start(client)
    start(client,'Guided','guided')
    progress=client.get('/progress').json()
    assert progress['totals']['conversations']==4
    assert progress['trend'][-1]['ai_first_ratio']==0.5
    assert client.get('/progress?experience=guided').json()['trend'][-1]['ai_first_ratio'] is None
    assert progress['totals']['own_attempts']==2
    assert progress['totals']['ai_answers']==2
    assert progress['totals']['ai_reviews']==1
    assert progress['modes']=={'own_only':1,'ai_only':1,'both':1,'no_saved_work':1}
    assert sum(w['own_attempts'] for w in progress['weeks'])==2
    assert client.get('/progress?experience=guided').json()['totals']['conversations']==1
    assert client.get('/progress?experience=all').status_code==422


def test_review_is_cached_resumable_separate_and_available_after_completion(client,learner):
    sid=start(client)
    answer(client,sid)
    client.post(f'/sessions/{sid}/close',json={'event_id':uid(),'final_status':'solved_with_ai'})
    eid=uid()
    before=client.get('/ai/usage').json()['requests_used']
    first=review(client,sid,eid)
    assert first.status_code==200,first.text
    assert review(client,sid,eid).json()['id']==first.json()['id']
    assert review(client,sid).json()['id']==first.json()['id']
    assert client.get('/ai/analyses/'+eid).json()['status']=='delivered'
    assert client.get('/ai/usage').json()['requests_used']==before+1
    assert learner['calls'][-1][-1]=='analysis'
    data=client.get('/sessions/'+sid).json()
    assert data['status']=='closed' and data['summary']['ai_requests']==1
    assert data['overview']['ai_answers']==1 and data['overview']['ai_reviews']==1
    assert not data['practice']['eligible']
    app.dependency_overrides[identity]=lambda:'not-the-review-owner'
    assert client.get('/ai/analyses/'+eid).status_code==404
    assert review(client,sid).status_code==404


def test_review_refresh_requires_changed_source_and_does_not_run_on_reads(client,learner):
    sid=start(client)
    assert review(client,sid).status_code==409
    emit(client,sid,'attempt_submitted',{'attempt_text':'My own approach'})
    first=review(client,sid).json()
    client.get('/history');client.get('/progress');client.get('/sessions/'+sid)
    assert len(learner['calls'])==1
    client.post(f'/sessions/{sid}/title',json={'title':'Renamed'})
    emit(client,sid,'conversation_mode_changed',{'mode':'try_myself'})
    assert review(client,sid).json()['id']==first['id']
    emit(client,sid,'attempt_submitted',{'attempt_text':'A refined approach'})
    second=review(client,sid).json()
    assert second['id']!=first['id'] and len(learner['calls'])==2
    assert review(client,start(client,'Study','guided')).status_code==409


def test_review_budget_failure_and_interrupted_request_do_not_replay(client,learner,monkeypatch):
    sid=start(client)
    emit(client,sid,'attempt_submitted',{'attempt_text':'A saved thought'})
    monkeypatch.setenv('AI_GLOBAL_DAILY_TOKENS','1')
    assert review(client,sid).status_code==429
    assert not learner['calls']
    monkeypatch.setenv('AI_GLOBAL_DAILY_TOKENS','1000000000')
    eid=uid()
    with SessionLocal() as db:
        db.add(Event(id=eid,user_id=learner['id'],session_id=sid,event_type='ai_analysis_requested',payload={},created_at=now()-timedelta(seconds=100)))
        db.commit()
    assert client.get('/ai/analyses/'+eid).json()['status']=='failed'
    assert review(client,sid,eid).status_code==502
    assert not learner['calls']


def test_review_actual_routing_uses_budget_usage_and_analysis_prompt(client,learner,monkeypatch):
    # Restore the real router; only the transport is synthetic.
    monkeypatch.setattr(routing,'generate',REAL_GENERATE)
    monkeypatch.setenv('AI_PROVIDER','groq');monkeypatch.setenv('AI_FALLBACK_ORDER','groq,gemini')
    monkeypatch.setenv('GROQ_API_KEY','synthetic');monkeypatch.setenv('GEMINI_API_KEY','synthetic')
    calls=[]
    def handle(request):
        body=json.loads(request.content);calls.append(body)
        if request.url.host=='api.groq.com':return httpx.Response(503)
        assert body['systemInstruction']['parts'][0]['text']==provider.ANALYSIS_PROMPT
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'Your saved attempt traces a loop. Try a second input.'}]}}],
            'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':20,'totalTokenCount':120}})
    real=httpx.AsyncClient
    monkeypatch.setattr(provider.httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(handle),**kwargs))
    sid=start(client)
    emit(client,sid,'attempt_submitted',{'attempt_text':'I traced one loop iteration.'})
    eid=uid();result=review(client,sid,eid)
    assert result.status_code==200,result.text
    assert result.json()['payload']['provider']=='gemini'
    assert len(calls)==2
    with SessionLocal() as db:
        row=db.get(AIUsageRequest,eid)
        assert row.accounted_tokens==row.attempt_budget+120 and row.status=='finished'
    data=client.get('/sessions/'+sid).json()
    assert data['summary']['ai_requests']==0 and data['overview']['ai_reviews']==1


def test_analysis_context_is_bounded_and_excludes_prior_reviews():
    events=[dict(id=uid(),event_type='session_started',payload={'problem_text':'Question','problem_domain':'math'},created_at=now().isoformat())]
    events += [dict(id=uid(),event_type='attempt_submitted',payload={'attempt_text':'x'*3000},created_at=now().isoformat()) for _ in range(30)]
    events.append(dict(id=uid(),event_type='ai_analysis_delivered',payload={'text':'PRIOR_REVIEW_SHOULD_NOT_BE_INPUT'},created_at=now().isoformat()))
    text,_,truncated=activity.analysis_context(events)
    assert truncated and 'PRIOR_REVIEW_SHOULD_NOT_BE_INPUT' not in text
    assert sum(len(e['text']) for e in json.loads(text)['excerpts'])<=16000
    assert json.loads(text)['original_question']=='Question'
