from uuid import uuid4
import pytest
from apps.api.auth import identity
from apps.api.main import app
from apps.api import provider, routing
from apps.api.db import engine
from apps.api.erase import fulfill


def uid():return str(uuid4())


@pytest.fixture
def owner(client):
    subject='workspace-'+uid()
    app.dependency_overrides[identity]=lambda:subject
    try:yield subject
    finally:app.dependency_overrides.pop(identity,None)


def start(client):
    result=client.post('/sessions',json={'event_id':uid(),'problem_domain':'math','problem_text':'How do I multiply 5 by 9?','experience':'chat'})
    assert result.status_code==201
    return result.json()['id']


def post_event(client,sid,kind,payload):
    return client.post('/events',json={'event_id':uid(),'session_id':sid,'event_type':kind,'payload':payload})


def test_language_and_exercise_preserve_focus_and_request_replay(client,owner,monkeypatch):
    calls=[]
    def generate(*args,**kwargs):
        calls.append((args,kwargs))
        return provider.Generation('What is 6 times 7?' if kwargs.get('purpose')=='exercise' else '42')
    monkeypatch.setattr(routing,'generate',generate)
    assert client.post('/preferences/language',json={'answer_language':'hindi'}).status_code==200
    sid=start(client)
    request={'event_id':uid(),'session_id':sid,'tier':3,'help_action':'exercise','followup_text':'Give me a related question.'}
    result=client.post('/ai/hint',json=request)
    assert result.status_code==200,result.text
    assert calls[-1][1]=={'language':'hindi','purpose':'exercise'}
    assert result.json()['payload']['answer_language']=='hindi'
    assert client.get('/sessions/'+sid).json()['mode']=='try_myself'
    assert client.post('/ai/hint',json=request).json()['id']==result.json()['id']
    assert len(calls)==1
    assert post_event(client,sid,'attempt_submitted',{'attempt_text':'42','is_partial':False}).status_code==200
    result=client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':3,'help_action':'answer','followup_text':'Explain the answer.'})
    assert result.status_code==200,result.text
    assert calls[-1][0][1:3]==('What is 6 times 7?','42')
    assert calls[-1][1]=={'language':'hindi'}
    assert client.post('/preferences/language',json={'answer_language':'invented'}).status_code==422
    assert client.post('/preferences/language',json={'answer_language':'english'}).status_code==200
    assert client.post('/ai/hint',json=request).json()['payload']['answer_language']=='hindi'
    assert len(calls)==2


def test_language_in_provider_prompt_and_every_fallback(monkeypatch):
    for purpose in ('answer','analysis','exercise'):
        system,_=provider.prompt_context(3,'Question','',[],purpose=purpose,language='hinglish')
        assert 'Latin script (Hinglish)' in system
    monkeypatch.setenv('GROQ_API_KEY','synthetic')
    monkeypatch.setenv('GEMINI_API_KEY','synthetic')
    monkeypatch.setenv('AI_FALLBACK_ORDER','groq,gemini')
    seen=[]
    async def generate(*args,**kwargs):
        seen.append((args[4],kwargs.get('language')))
        if args[4]=='groq':raise provider.ProviderError('Synthetic outage')
        return provider.Generation('नमस्ते')
    monkeypatch.setattr(provider,'generate_async',generate)
    result=routing.generate(3,'Question','',[],preferred='groq',language='hindi')
    assert result.text=='नमस्ते'
    assert seen==[('groq','hindi'),('gemini','hindi')]


def test_goals_count_distinct_retries_and_do_not_reset_on_edit(client,owner,monkeypatch):
    monkeypatch.setattr(routing,'generate',lambda *a,**k:provider.Generation('45'))
    assert client.post('/learning-goal',json={'goal':'','weekly_target':3}).status_code==422
    assert client.post('/learning-goal',json={'goal':'Math reasoning','weekly_target':3}).status_code==200
    assert client.post('/preferences/language',json={'answer_language':'hinglish'}).status_code==200
    sid=start(client)
    aid=client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':3}).json()['id']
    assert post_event(client,sid,'answer_saved',{'answer_event_id':aid,'saved':True}).status_code==200
    for text in ('Five groups of nine.','Half of ninety.'):
        assert post_event(client,sid,'learning_attempt_submitted',{'answer_event_id':aid,'attempt_text':text}).status_code==200
    value=client.get('/learning-goal').json()
    assert (value['questions_retried'],value['attempts'])==(1,2)
    assert value['answer_language']=='hinglish'
    assert client.post('/learning-goal',json={'goal':'A clearer explanation','weekly_target':5}).json()['questions_retried']==1
    assert client.post('/learning-goal',json={'goal':'A clearer explanation','weekly_target':0}).json()['questions_retried']==1
    post_event(client,sid,'answer_saved',{'answer_event_id':aid,'saved':False})
    assert client.get('/learning-goal').json()['questions_retried']==1
    app.dependency_overrides[identity]=lambda:'other-'+owner
    assert client.get('/learning-goal').json()['questions_retried']==0
    assert client.get('/preferences/language').json()['answer_language']=='auto'


def test_reports_replay_owner_isolation_operator_access_and_rate_limit(client,owner,monkeypatch):
    body={'id':uid(),'category':'accessibility','message':'The mobile button is difficult to reach.','reference':uid()}
    first=client.post('/support/reports',json=body)
    assert first.status_code==201,first.text
    assert client.post('/support/reports',json=body).json()['id']==body['id']
    assert client.post('/support/reports',json={**body,'message':'A different report body'}).status_code==409
    assert len(client.get('/support/reports').json())==1
    monkeypatch.setenv('AUTH_MODE','clerk')
    assert client.get('/operator/reports').status_code==403
    monkeypatch.setenv('ADMIN_SUBJECTS',owner)
    assert client.get('/operator/reports').status_code==200
    # Notice acknowledgment remains required for mutations in hosted mode.
    client.post('/privacy',json={'research_opt_in':False,'acknowledge_notice':True})
    assert client.post('/operator/reports/'+body['id'],json={'status':'resolved'}).status_code==200
    assert client.get('/support/reports').json()[0]['status']=='resolved'
    monkeypatch.setenv('AUTH_MODE','development')
    for _ in range(9):assert client.post('/support/reports',json={**body,'id':uid()}).status_code==201
    assert client.post('/support/reports',json={**body,'id':uid()}).status_code==429
    assert client.post('/support/reports',json=body).status_code==201
    app.dependency_overrides[identity]=lambda:'outsider-'+owner
    assert client.get('/support/reports').json()==[]
    assert client.post('/support/reports',json=body).status_code==409


def test_goal_language_and_reports_export_and_full_erasure(client,owner):
    client.post('/learning-goal',json={'goal':'Private learning goal','weekly_target':4})
    client.post('/preferences/language',json={'answer_language':'hindi'})
    body={'id':uid(),'category':'problem','message':'Private report chosen by the user.'}
    assert client.post('/support/reports',json=body).status_code==201
    exported=client.get('/privacy/export').json()
    assert exported['learning_preferences']['goal']=='Private learning goal'
    assert exported['support_reports'][0]['id']==body['id']
    request=client.post('/privacy/deletion',json={'confirmation':'DELETE MY CONVERSATIONS'}).json()['deletion_request']
    assert client.post('/support/reports',json={**body,'id':uid()}).status_code==409
    with engine.begin() as connection:assert fulfill(connection,request['id'],request['user_id'])
    assert client.get('/support/reports').json()==[]
    assert client.get('/learning-goal').json()['goal']==''
    assert client.get('/preferences/language').json()['answer_language']=='auto'
