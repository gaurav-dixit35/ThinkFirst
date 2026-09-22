from uuid import uuid4
from apps.api import provider,routing
from apps.api.auth import identity
from apps.api.main import app
from apps.api.chat_context import LEGACY_ACTIONS

def uid(): return str(uuid4())


def test_changed_topic_help_uses_current_question_and_attempt(client,monkeypatch):
    calls=[]
    monkeypatch.setattr(routing,'generate',lambda *args:calls.append(args) or provider.Generation('Synthetic answer.'))
    sid=client.post('/sessions',json={'event_id':uid(),'problem_domain':'general_reasoning','problem_text':'My smartphone is overheating','experience':'chat'}).json()['id']
    def ask(**extra):
        body={'event_id':uid(),'session_id':sid,'tier':3,**extra}
        result=client.post('/ai/hint',json=body)
        assert result.status_code==200,result.text
        return body,result
    ask()
    ask(followup_text='5*5')
    ask(followup_text='5*9')
    assert client.post('/events',json={'event_id':uid(),'session_id':sid,'event_type':'attempt_submitted','payload':{'attempt_text':'45','is_partial':True}}).status_code==200
    for _ in range(2):
        body,result=ask(tier=2,help_action='hint',followup_text='Give me a hint for the current question.')
        assert calls[-1][1:3]==('5*9','45')
        assert result.json()['payload']['focus_question']=='5*9'
        assert calls[-1][3]==[]
        assert client.post('/ai/hint',json=body).json()['id']==result.json()['id']
    ask(help_action='answer',followup_text='Show an answer to the current question.')
    assert calls[-1][1:3]==('5*9','45')
    # The old buttons in previously saved chats must not reset the topic either.
    for text in LEGACY_ACTIONS:
        ask(tier=2 if LEGACY_ACTIONS[text]=='hint' else 3,followup_text=text)
        assert calls[-1][1:3]==('5*9','45')
    ask(followup_text='Now help me write a poem')
    assert calls[-1][1:3]==('Now help me write a poem','')
    ask(help_action='answer')
    assert calls[-1][1:3]==('Now help me write a poem','')


def test_help_action_validation_and_request_replay(client,monkeypatch):
    monkeypatch.setattr(routing,'generate',lambda *args:provider.Generation('Synthetic answer.'))
    sid=client.post('/sessions',json={'event_id':uid(),'problem_domain':'math','problem_text':'5*9','experience':'chat'}).json()['id']
    body={'event_id':uid(),'session_id':sid,'tier':2,'help_action':'hint'}
    assert client.post('/ai/hint',json={**body,'tier':3}).status_code==422
    assert client.post('/ai/hint',json=body).status_code==200
    assert client.post('/ai/hint',json={**body,'help_action':'answer'}).status_code==409


def test_answer_preferences_are_private_and_exported(client):
    first='preference-'+uid()
    app.dependency_overrides[identity]=lambda:first
    try:
        assert client.get('/preferences/answers').json()['answer_style']=='concise'
        assert client.post('/preferences/answers',json={'answer_style':'detailed'}).status_code==200
        sid=client.post('/sessions',json={'event_id':uid(),'problem_domain':'math','problem_text':'5*9','experience':'chat'}).json()['id']
        assert client.get('/sessions/'+sid).json()['answer_style']=='detailed'
        assert client.get('/privacy/export').json()['answer_preferences']['answer_style']=='detailed'
        assert client.post('/preferences/answers',json={'answer_style':'invalid'}).status_code==422
        app.dependency_overrides[identity]=lambda:'preference-'+uid()
        assert client.get('/preferences/answers').json()['answer_style']=='concise'
    finally:
        app.dependency_overrides.pop(identity,None)
