"""Phase 1 API checks. Provider responses are mocked; no live keys are used."""
from uuid import uuid4
from apps.api import provider, routing


def uid():
    return str(uuid4())


def start(client, mode='ask_ai', **extra):
    body={'event_id':uid(),'problem_domain':'math','problem_text':'Solve 2x + 3 = 11',
          'experience':'chat','initial_mode':mode,**extra}
    response=client.post('/sessions',json=body)
    assert response.status_code==201, response.text
    return response.json()['id'],body


def emit(client,sid,kind,payload):
    return client.post('/events',json={'event_id':uid(),'session_id':sid,'event_type':kind,'payload':payload})


def test_chat_starts_with_answer_and_continues_without_reflection_gates(client,monkeypatch):
    calls=[]
    def generate(*args):
        calls.append(args)
        return provider.Generation('Subtract 3 and divide by 2: x is 4.')
    monkeypatch.setattr(routing,'generate',generate)
    sid,_=start(client)
    body={'event_id':uid(),'session_id':sid,'tier':3,'provider':'auto'}
    first=client.post('/ai/hint',json=body)
    assert first.status_code==200,first.text
    assert first.json()['payload']['request_kind']=='answer'
    assert client.post('/ai/hint',json=body).json()['id']==first.json()['id']
    second=client.post('/ai/hint',json={**body,'event_id':uid(),'followup_text':'Why divide by 2?'})
    assert second.status_code==200,second.text
    assert calls[-1][5]==[{'role':'assistant','content':first.json()['payload']['hint_text']}]
    assert calls[-1][6]=='Why divide by 2?'
    data=client.get('/sessions/'+sid).json()
    assert data['experience']=='chat' and data['mode']=='ask_ai'
    assert data['summary']['ai_requests']==2
    assert not any(e['event_type'] in ('attempt_skipped','verification_skipped','evaluation_skipped') for e in data['events'])
    result=client.post('/sessions/'+sid+'/close',json={'event_id':uid(),'final_status':'solved_with_ai'})
    assert result.status_code==200,result.text


def test_try_myself_switches_mode_and_requests_hint_in_same_conversation(client,monkeypatch):
    calls=[]
    monkeypatch.setattr(routing,'generate',lambda *args:(calls.append(args) or provider.Generation('Consider inverse operations.')))
    sid,_=start(client,'try_myself')
    assert not calls
    assert emit(client,sid,'attempt_submitted',{'attempt_text':'Subtract 3 first','is_partial':True}).status_code==200
    assert client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':2}).status_code==200
    assert calls[0][2]=='Subtract 3 first'
    assert emit(client,sid,'conversation_mode_changed',{'mode':'ask_ai'}).status_code==200
    assert client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':3,'followup_text':'Show the answer'}).status_code==200
    assert emit(client,sid,'conversation_mode_changed',{'mode':'try_myself'}).status_code==200
    assert client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':2,'followup_text':'Give me one hint to check my answer'}).status_code==200
    data=client.get('/sessions/'+sid).json()
    assert data['mode']=='try_myself'
    assert data['status']=='open'
    assert data['summary']['initial_mode']=='try_myself'
    assert data['summary']['experience']=='chat'
    assert len([e for e in data['events'] if e['event_type']=='attempt_submitted'])==1
    assert len(calls)==3


def test_mode_changes_are_idempotent_and_cannot_be_forged_on_guided_sessions(client):
    sid,_=start(client)
    body={'event_id':uid(),'session_id':sid,'event_type':'conversation_mode_changed','payload':{'mode':'try_myself'}}
    first=client.post('/events',json=body)
    assert first.status_code==200
    assert client.post('/events',json=body).json()['id']==first.json()['id']
    assert client.post('/events',json={**body,'payload':{'mode':'ask_ai'}}).status_code==409
    guided,_=start(client,experience='guided')
    assert emit(client,guided,'conversation_mode_changed',{'mode':'try_myself'}).status_code==409
    assert client.post('/ai/hint',json={'event_id':uid(),'session_id':guided,'tier':3}).status_code==409


def test_conversation_start_retries_preserve_protocol_and_mode(client):
    sid,body=start(client)
    assert client.post('/sessions',json=body).json()['id']==sid
    assert client.post('/sessions',json={**body,'experience':'guided'}).status_code==409
    assert client.post('/sessions',json={**body,'initial_mode':'try_myself'}).status_code==409


def test_followup_requires_new_intent_and_finished_chats_cannot_change(client,monkeypatch):
    monkeypatch.setattr(routing,'generate',lambda *args:provider.Generation('Answer'))
    sid,_=start(client)
    assert client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':3}).status_code==200
    assert client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':3}).status_code==409
    assert client.post('/sessions/'+sid+'/close',json={'event_id':uid(),'final_status':'solved_with_ai'}).status_code==200
    assert emit(client,sid,'conversation_mode_changed',{'mode':'try_myself'}).status_code==409


def test_research_does_not_silently_pool_chat_and_guided_sessions(client,monkeypatch):
    monkeypatch.setenv('ADMIN_SUBJECTS','local-development-participant')
    before=client.get('/analytics/research').json()['session_count']
    chats=client.get('/analytics/research?experience=chat').json()['session_count']
    start(client)
    guided_result=client.get('/analytics/research').json()
    assert guided_result['experience']=='guided'
    assert guided_result['session_count']==before
    assert client.get('/analytics/research?experience=chat').json()['session_count']==chats+1
    assert client.get('/analytics/research?experience=all').status_code==400
