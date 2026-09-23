from uuid import uuid4
import pytest
from apps.api.auth import identity
from apps.api.main import app
from apps.api import provider, routing
from apps.api.db import engine
from apps.api.erase import fulfill


def uid():
    return str(uuid4())


@pytest.fixture
def learner(client, monkeypatch):
    subject = 'saved-learning-' + uid()
    app.dependency_overrides[identity] = lambda: subject
    calls = []
    def generate(*args, **kwargs):
        calls.append(args)
        return provider.Generation('Forty-five: 5 times 9 = 45.')
    monkeypatch.setattr(routing, 'generate', generate)
    try:
        yield subject, calls
    finally:
        app.dependency_overrides.pop(identity, None)


def conversation(client, question='How can I cool a phone?'):
    result = client.post('/sessions', json={'event_id':uid(),'problem_domain':'general_reasoning','problem_text':question,'experience':'chat'})
    assert result.status_code == 201, result.text
    return result.json()['id']


def answer(client, sid, question='What is 5 times 9?'):
    response = client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':3,'followup_text':question})
    assert response.status_code == 200, response.text
    return response.json()['id']


def emit(client, sid, kind, payload, event_id=None):
    return client.post('/events',json={'event_id':event_id or uid(),'session_id':sid,'event_type':kind,'payload':payload})


def save(client, sid, aid, saved=True):
    return emit(client,sid,'answer_saved',{'answer_event_id':aid,'saved':saved})


def test_saved_retry_uses_correct_question_no_ai_and_preserves_original_metrics(client, learner):
    _, calls = learner
    sid = conversation(client)
    aid = answer(client,sid)
    assert save(client,sid,aid).status_code == 200
    item = client.get('/saved/'+aid).json()
    assert item['question'] == 'What is 5 times 9?'
    assert client.post('/sessions/'+sid+'/close',json={'event_id':uid(),'final_status':'solved_with_ai'}).status_code == 200
    before = client.get('/progress').json()['totals']
    request_id = uid()
    payload = {'answer_event_id':aid,'attempt_text':'Half of 90 is 45.'}
    first = emit(client,sid,'learning_attempt_submitted',payload,request_id)
    assert first.status_code == 200, first.text
    assert emit(client,sid,'learning_attempt_submitted',payload,request_id).json()['id'] == first.json()['id']
    assert emit(client,sid,'learning_attempt_submitted',{**payload,'attempt_text':'Different'},request_id).status_code == 409
    assert client.get('/saved').json()['summary'] == {'saved':1,'retried':1,'attempts':1}
    assert client.get('/saved?unpractised=true').json()['total'] == 0
    assert client.get('/saved?q=forty-five').json()['total'] == 1
    assert client.get('/progress').json()['totals'] == before
    assert len(calls) == 1
    assert 'Half of 90 is 45.' in client.get('/privacy/export').text
    assert save(client,sid,aid,False).status_code == 200
    assert client.get('/saved/'+aid).status_code == 404
    assert client.get('/saved').json()['total'] == 0
    assert save(client,sid,aid).status_code == 200
    assert len(client.get('/saved/'+aid).json()['attempts']) == 1


def test_saved_answers_are_owner_and_conversation_scoped(client, learner):
    subject, _ = learner
    sid = conversation(client)
    aid = answer(client,sid)
    assert save(client,sid,aid).status_code == 200
    other_sid = conversation(client,'Different conversation')
    assert save(client,other_sid,aid).status_code == 400
    app.dependency_overrides[identity] = lambda:'outsider-'+subject
    assert client.get('/saved').json()['total'] == 0
    assert client.get('/saved/'+aid).status_code == 404
    assert save(client,sid,aid).status_code == 404
    outsider_sid = conversation(client)
    assert save(client,outsider_sid,aid).status_code == 400


def test_retry_requires_saved_answer_and_pending_erasure_blocks_writes(client, learner):
    sid = conversation(client)
    aid = answer(client,sid)
    payload = {'answer_event_id':aid,'attempt_text':'My retry'}
    assert emit(client,sid,'learning_attempt_submitted',payload).status_code == 409
    assert save(client,sid,aid).status_code == 200
    assert emit(client,sid,'learning_attempt_submitted',{**payload,'attempt_text':'  '}).status_code == 422
    assert emit(client,sid,'learning_attempt_submitted',payload).status_code == 200
    request = client.post('/sessions/'+sid+'/deletion',json={'confirmation':'DELETE THIS CONVERSATION'})
    assert request.status_code == 202
    assert client.get('/saved/'+aid).json()['deletion_pending'] is True
    assert save(client,sid,aid,False).status_code == 409
    assert emit(client,sid,'learning_attempt_submitted',payload).status_code == 409
    with engine.begin() as connection:
        assert fulfill(connection,request.json()['id'],request.json()['user_id'])
    assert client.get('/saved/'+aid).status_code == 404
    assert client.get('/saved').json()['total'] == 0
    assert 'My retry' not in client.get('/privacy/export').text


def test_bookmark_replay_pagination_and_regenerated_question(client, learner):
    sid = conversation(client)
    aid = answer(client,sid)
    regen = client.post('/ai/hint',json={'event_id':uid(),'session_id':sid,'tier':3,'followup_text':'What is 5 times 9?','regenerate_of':aid})
    assert regen.status_code == 200, regen.text
    replacement = regen.json()['id']
    event_id = uid()
    payload = {'answer_event_id':aid,'saved':True}
    first = emit(client,sid,'answer_saved',payload,event_id)
    assert emit(client,sid,'answer_saved',payload,event_id).json()['id'] == first.json()['id']
    assert save(client,sid,replacement).status_code == 200
    assert client.get('/saved/'+replacement).json()['question'] == 'What is 5 times 9?'
    page = client.get('/saved?limit=1').json()
    assert page['total'] == 2 and page['has_more'] is True and len(page['items']) == 1
    next_page = client.get('/saved?limit=1&offset=1').json()
    assert next_page['items'][0]['answer_id'] != page['items'][0]['answer_id']
    assert next_page['has_more'] is False
