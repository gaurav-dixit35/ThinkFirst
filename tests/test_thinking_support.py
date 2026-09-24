from uuid import uuid4
import json
import pytest
from apps.api import provider, routing, question_tracking
from apps.api.auth import identity
from apps.api.main import app


def uid(): return str(uuid4())


@pytest.fixture
def learner(client, monkeypatch):
    subject = 'thinking-' + uid()
    app.dependency_overrides[identity] = lambda: subject
    calls = []
    def generate(*args, **kwargs):
        calls.append((args, kwargs))
        return provider.Generation('Which operation leaves x by itself?')
    monkeypatch.setattr(routing, 'generate', generate)
    try:
        yield subject, calls
    finally:
        app.dependency_overrides.pop(identity, None)


def start(client, text='My phone is hot', experience='chat'):
    body = {'event_id': uid(), 'problem_text': text, 'problem_domain': 'general_reasoning',
            'experience': experience, 'initial_mode': 'try_myself'}
    result = client.post('/sessions', json=body)
    assert result.status_code == 201, result.text
    return result.json()['id'], body['event_id']


def emit(client, sid, kind, payload, eid=None):
    return client.post('/events', json={'event_id': eid or uid(), 'session_id': sid, 'event_type': kind, 'payload': payload})


def ask(client, sid, **extra):
    return client.post('/ai/hint', json={'event_id': uid(), 'session_id': sid, 'tier': 3, **extra})


def test_check_requires_current_attempt_before_usage_and_preserves_mode(client, learner):
    _, calls = learner
    sid, anchor = start(client)
    before = client.get('/ai/usage').json()['requests_used']
    assert ask(client, sid, help_action='check_thinking').status_code == 409
    assert client.get('/ai/usage').json()['requests_used'] == before
    assert not calls
    eid = uid()
    payload = {'attempt_text': 'Stop charging and let it rest.', 'is_partial': True}
    saved = emit(client, sid, 'attempt_submitted', payload, eid)
    assert saved.status_code == 200
    assert saved.json()['payload']['question_event_id'] == anchor
    assert emit(client, sid, 'attempt_submitted', payload, eid).json()['id'] == eid
    body = {'event_id': uid(), 'session_id': sid, 'tier': 3, 'help_action': 'check_thinking'}
    response = client.post('/ai/hint', json=body)
    assert response.status_code == 200, response.text
    assert calls[-1][0][1:3] == ('My phone is hot', payload['attempt_text'])
    assert calls[-1][1]['purpose'] == 'check_thinking'
    assert response.json()['payload']['question_event_id'] == anchor
    assert client.post('/ai/hint', json=body).json()['id'] == response.json()['id']
    assert len(calls) == 1
    assert client.get('/sessions/' + sid).json()['mode'] == 'try_myself'
    assert client.get('/sessions/' + sid).json()['question_tracking']['questions'][0]['attempt_before_first_request'] is True
    assert client.post('/ai/hint', json={**body, 'help_action': 'answer'}).status_code == 409
    ask(client, sid, followup_text='What is 5 times 9?')
    assert ask(client, sid, help_action='check_thinking').status_code == 409
    assert len(calls) == 2


def test_mixed_topics_late_attempts_and_regeneration_keep_question_reference(client, learner):
    _, calls = learner
    sid, phone = start(client)
    result = ask(client, sid, followup_text='What is 5 times 9?').json()
    maths = result['payload']['question_event_id']
    assert maths != phone
    # Offline work for the old question must not become a maths attempt.
    assert emit(client, sid, 'attempt_submitted', {'attempt_text': 'Stop charging.', 'question_event_id': phone}).status_code == 200
    assert ask(client, sid, help_action='check_thinking').status_code == 409
    assert emit(client, sid, 'attempt_submitted', {'attempt_text': '45', 'question_event_id': maths}).status_code == 200
    feedback = ask(client, sid, help_action='check_thinking').json()
    assert calls[-1][0][1:3] == ('What is 5 times 9?', '45')
    regenerated = ask(client, sid, help_action='check_thinking', regenerate_of=feedback['id'])
    assert regenerated.status_code == 200, regenerated.text
    assert regenerated.json()['payload']['question_event_id'] == maths
    tracking = client.get('/sessions/' + sid).json()['question_tracking']
    assert len(tracking['questions']) == 2
    assert [q['attempts'] for q in tracking['questions']] == [1, 1]
    assert tracking['questions'][1]['requests']['check_thinking'] == 2
    assert tracking['questions'][0]['attempt_before_first_request'] is None
    assert tracking['questions'][1]['attempt_before_first_request'] is False
    # A regeneration of a typed question keeps its original request anchor.
    sid2, _ = start(client)
    answer = ask(client, sid2, followup_text='What is 2 plus 2?').json()
    again = ask(client, sid2, followup_text='What is 2 plus 2?', regenerate_of=answer['id'])
    assert again.json()['payload']['question_event_id'] == answer['payload']['question_event_id']
    assert len(client.get('/sessions/' + sid2).json()['question_tracking']['questions']) == 2


def test_verification_revisions_are_optional_private_and_do_not_change_old_metrics(client, learner):
    subject, calls = learner
    sid, anchor = start(client)
    answer = ask(client, sid).json()
    client.post('/sessions/' + sid + '/close', json={'event_id': uid(), 'final_status': 'solved_with_ai'})
    before = client.get('/sessions/' + sid).json()['summary']
    eid = uid()
    payload = {'answer_event_id': answer['id'], 'status': 'checked', 'method': 'source', 'note': 'Compared with the manual.'}
    saved = emit(client, sid, 'answer_verification_reported', payload, eid)
    assert saved.status_code == 200, saved.text
    assert saved.json()['payload']['question_event_id'] == anchor
    assert emit(client, sid, 'answer_verification_reported', payload, eid).json()['id'] == eid
    assert emit(client, sid, 'answer_verification_reported', {**payload, 'note': 'Different'}, eid).status_code == 409
    revision = emit(client, sid, 'answer_verification_reported', {**payload, 'status': 'found_issue'})
    assert revision.status_code == 200
    current = client.get('/sessions/' + sid).json()
    assert current['summary'] == before
    assert current['question_tracking']['questions'][0]['verification'] == {'checked': 0, 'found_issue': 1, 'not_checked': 0}
    assert len(calls) == 1
    assert 'Compared with the manual.' in client.get('/privacy/export').text
    other, _ = start(client)
    assert emit(client, other, 'answer_verification_reported', payload).status_code == 400
    app.dependency_overrides[identity] = lambda: 'outsider-' + subject
    assert emit(client, sid, 'answer_verification_reported', payload).status_code == 404


def test_verification_validation_and_pending_deletion(client, learner):
    sid, _ = start(client)
    answer = ask(client, sid).json()
    payload = {'answer_event_id': answer['id'], 'status': 'checked'}
    assert emit(client, sid, 'answer_verification_reported', payload).status_code == 422
    assert emit(client, sid, 'answer_verification_reported', {**payload, 'status': 'not_checked', 'method': 'source'}).status_code == 422
    assert emit(client, sid, 'answer_verification_reported', {**payload, 'status': 'not_checked'}).status_code == 200
    exercise = ask(client, sid, help_action='exercise').json()
    assert emit(client, sid, 'answer_verification_reported', {**payload, 'answer_event_id': exercise['id'], 'method': 'example'}).status_code == 422
    assert emit(client, sid, 'attempt_submitted', {'attempt_text': 'Guess', 'question_event_id': uid()}).status_code == 422
    assert client.post('/sessions/' + sid + '/deletion', json={'confirmation': 'DELETE THIS CONVERSATION'}).status_code == 202
    assert emit(client, sid, 'answer_verification_reported', {**payload, 'method': 'source'}).status_code == 409


def test_exercise_anchor_and_guided_protocol_unchanged(client, learner):
    sid, _ = start(client)
    exercise = ask(client, sid, help_action='exercise').json()
    attempt = emit(client, sid, 'attempt_submitted', {'attempt_text': 'Divide both sides.'})
    assert attempt.json()['payload']['question_event_id'] == exercise['id']
    assert ask(client, sid, help_action='check_thinking').json()['payload']['question_event_id'] == exercise['id']
    guided, _ = start(client, experience='guided')
    assert ask(client, guided, help_action='check_thinking').status_code == 422
    assert client.get('/sessions/' + guided).json()['question_tracking'] is None


def test_thinking_prompt_reaches_every_fallback(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic')
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic')
    monkeypatch.setenv('AI_FALLBACK_ORDER', 'groq,gemini')
    seen = []
    async def generate(*args, **kwargs):
        seen.append((args[4], args[8], kwargs.get('language')))
        if args[4] == 'groq':
            raise provider.ProviderError('Synthetic outage')
        return provider.Generation('What would you do next?')
    monkeypatch.setattr(provider, 'generate_async', generate)
    routing.generate(3, '2x+3=11', '2x=8', [], preferred='groq', purpose='check_thinking', language='hindi')
    assert seen == [('groq', 'check_thinking', 'hindi'), ('gemini', 'check_thinking', 'hindi')]
    prompt, data = provider.prompt_context(3, '2x+3=11', '2x=8', [], purpose='check_thinking', language='hindi')
    assert 'Do not supply a worked solution' in prompt
    assert 'do not invent a mistake' in prompt and 'Devanagari' in prompt
    assert json.loads(data)['attempt'] == '2x=8'


def test_invalidated_anchor_does_not_reassign_old_work():
    events = [{'id':'start','event_type':'session_started','payload':{'problem_text':'First'}},
              {'id':'attempt','event_type':'attempt_submitted','payload':{'attempt_text':'Old work','question_event_id':'invalidated'}}]
    result = question_tracking.view(events)
    assert result['questions'][0]['attempts'] == 0
    assert 'attempt' not in result['event_questions']
