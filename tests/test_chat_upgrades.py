import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import httpx
import pytest
from sqlalchemy import select
from apps.api import provider, routing
from apps.api.db import SessionLocal, Session, Event, ResponseDraft, AIUsageRequest, engine
from apps.api.erase import fulfill
from apps.api.provider_stream import read


def start(client, text='What is 5 times 9?'):
    response=client.post('/sessions',json={'event_id':str(uuid4()),'problem_domain':'math','problem_text':text,'experience':'chat'})
    assert response.status_code==201,response.text
    return response.json()['id']


def test_edit_forks_earlier_context_without_rewriting_and_regeneration_replays(client,monkeypatch):
    calls=[]
    def generate(*args,**kwargs):
        calls.append(args)
        return provider.Generation('45')
    monkeypatch.setattr(routing,'generate',generate)
    sid=start(client)
    request={'session_id':sid,'event_id':str(uuid4()),'tier':3}
    first=client.post('/ai/hint',json=request).json()
    regen={**request,'event_id':str(uuid4()),'regenerate_of':first['id']}
    answer=client.post('/ai/hint',json=regen)
    assert answer.status_code==200,answer.text
    assert all(m['role']!='assistant' for m in calls[-1][5])
    assert client.post('/ai/hint',json=regen).json()['id']==answer.json()['id']
    assert len(calls)==2
    assert client.post('/ai/hint',json={**regen,'event_id':str(uuid4()),'followup_text':'Different question'}).status_code==409
    events=client.get('/sessions/'+sid).json()['events']
    edit={'event_id':str(uuid4()),'source_event_id':events[0]['id'],'question':'What is 5 times 8?'}
    branch=client.post(f'/sessions/{sid}/edit-question',json=edit)
    assert branch.status_code==201,branch.text
    assert client.post(f'/sessions/{sid}/edit-question',json=edit).json()==branch.json()
    assert client.get('/sessions/'+sid).json()['events']==events
    assert client.get('/sessions/'+branch.json()['id']).json()['events'][0]['payload']['problem_text']==edit['question']


def test_archive_and_targeted_erasure_preserve_other_conversations(client):
    sid,other=start(client),start(client,'Keep me')
    assert client.post(f'/sessions/{sid}/archive',json={'archived':True}).status_code==200
    assert sid not in [x['id'] for x in client.get('/history').json()['items']]
    assert sid in [x['id'] for x in client.get('/history?folder=archived').json()['items']]
    assert client.post(f'/sessions/{sid}/archive',json={'archived':False}).status_code==200
    response=client.post(f'/sessions/{sid}/deletion',json={'confirmation':'DELETE THIS CONVERSATION'})
    assert response.status_code==202,response.text
    assert client.post('/events',json={'event_id':str(uuid4()),'session_id':sid,'event_type':'attempt_submitted','payload':{'attempt_text':'New work','is_partial':True}}).status_code==409
    assert client.post('/ai/hint',json={'event_id':str(uuid4()),'session_id':sid,'tier':3}).status_code==409
    assert sid in [x['id'] for x in client.get('/history?folder=deletion').json()['items']]
    request=response.json()
    with engine.begin() as connection:
        assert fulfill(connection,request['id'],request['user_id'])
        assert not fulfill(connection,request['id'],request['user_id'])
    assert client.get('/sessions/'+sid).status_code==404
    assert client.get('/sessions/'+other).status_code==200
    assert sid in client.get('/privacy').json()['erased_session_ids']


def test_stream_stop_is_persisted_and_charged_without_delivering_partial(client,monkeypatch):
    began=threading.Event()
    monkeypatch.setenv('GROQ_API_KEY','synthetic')
    async def generate(*args,**kwargs):
        kwargs['on_delta']('A partial preview')
        began.set()
        await asyncio.sleep(10)
        return provider.Generation('Should not be delivered')
    monkeypatch.setattr(provider,'generate_async',generate)
    sid=start(client)
    body={'session_id':sid,'event_id':str(uuid4()),'tier':3,'provider':'groq','stream':True}
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(client.post,'/ai/hint',json=body)
        assert began.wait(5)
        assert client.get('/ai/requests/'+body['event_id']).json()['preview']=='A partial preview'
        assert client.post('/ai/requests/'+body['event_id']+'/cancel',json={}).status_code==200
        response=future.result(timeout=5)
    assert response.status_code==499,response.text
    state=client.get('/ai/requests/'+body['event_id']).json()
    assert state['status']=='cancelled' and not state['preview']
    assert client.post('/ai/hint',json=body).status_code==499
    with SessionLocal() as db:
        ledger=db.get(AIUsageRequest,body['event_id'])
        assert ledger.status=='finished' and ledger.accounted_tokens>0
        assert ledger.attempts[0]['error_code']=='cancelled'


@pytest.mark.parametrize('name',['groq','openrouter','mistral','cloudflare','gemini','anthropic'])
def test_provider_stream_extracts_only_answer_text_and_requires_completion(name):
    if name=='gemini':
        chunks=[{'candidates':[{'content':{'parts':[{'text':'secret reasoning','thought':True},{'text':'Hello'}]}}]}, {'candidates':[{'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':2,'candidatesTokenCount':1}}]
    elif name=='anthropic':
        chunks=[{'type':'message_start','message':{'model':'synthetic','usage':{'input_tokens':2}}},{'type':'content_block_delta','delta':{'type':'thinking_delta','thinking':'secret reasoning'}},{'type':'content_block_delta','delta':{'type':'text_delta','text':'Hello'}},{'type':'message_delta','delta':{'stop_reason':'end_turn'},'usage':{'output_tokens':1}},{'type':'message_stop'}]
    else:
        chunks=[{'choices':[{'delta':{'reasoning':'secret reasoning','content':'Hello'}}]},{'choices':[{'delta':{},'finish_reason':'stop'}],'usage':{'prompt_tokens':2,'completion_tokens':1}},'[DONE]']
    wire=''.join('data: '+(x if isinstance(x,str) else json.dumps(x))+'\n\n' for x in chunks)
    previews=[]
    body=asyncio.run(read(httpx.Response(200,content=wire),name,previews.append))
    result=provider.parse_response(name,body)
    assert result.text=='Hello' and result.usage['total_tokens']==3
    assert previews==['Hello']
    with pytest.raises(ValueError):
        asyncio.run(read(httpx.Response(200,content='data: '+json.dumps(chunks[0])+'\n\n'),name,lambda text:None))


def test_fallback_replaces_preview_and_keeps_attempt_accounting(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','synthetic')
    monkeypatch.setenv('GEMINI_API_KEY','synthetic')
    async def generate(*args,**kwargs):
        kwargs['on_delta']('Partial first' if args[4]=='groq' else 'Second provider answer')
        if args[4]=='groq': raise ValueError('Interrupted')
        return provider.Generation('Second provider answer')
    monkeypatch.setattr(provider,'generate_async',generate)
    previews,reports=[],[]
    result=routing.generate(3,'Question','',[],preferred='groq',on_attempt=reports.append,on_delta=previews.append)
    assert result.text=='Second provider answer'
    assert previews==['','Partial first','','Second provider answer']
    assert [r['outcome'] for r in reports]==['failed','success']
