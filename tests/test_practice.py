from datetime import datetime, timedelta, timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from apps.api import practice, provider, routing
from apps.api.auth import identity
from apps.api.main import app
from apps.api.db import engine


def uid():
    return str(uuid4())


@pytest.fixture
def learner(client,monkeypatch):
    subject=uid()
    app.dependency_overrides[identity]=lambda:'practice-'+subject
    calls=[]
    monkeypatch.setattr(routing,'generate',lambda *args:calls.append(args) or provider.Generation('A useful answer.'))
    try:
        yield calls
    finally:
        app.dependency_overrides.pop(identity,None)


def chat(client,experience='chat'):
    return client.post('/sessions',json=dict(event_id=uid(),problem_domain='coding',problem_text='How does a loop work?',experience=experience)).json()['id']


def answer(client,sid,index=0):
    response=client.post('/ai/hint',json=dict(event_id=uid(),session_id=sid,tier=3,**({'followup_text':f'Explain example {index}'} if index else {})))
    assert response.status_code==200,response.text
    return response.json()['id']


def emit(client,sid,kind,payload,event_id=None):
    return client.post('/events',json=dict(event_id=event_id or uid(),session_id=sid,event_type=kind,payload=payload))


def ready(client):
    sid=chat(client)
    ids=[answer(client,sid,i) for i in range(3)]
    return sid,ids[-1]


def test_no_is_durable_idempotent_and_does_not_block_chat(client,learner):
    sid,target=ready(client)
    data=client.get('/sessions/'+sid).json()
    assert data['practice']['eligible'] and data['practice']['answer_event_id']==target
    eid=uid()
    payload=dict(answer_event_id=target,decision='continue_ai')
    first=emit(client,sid,'practice_invitation_responded',payload,eid)
    assert first.status_code==200,first.text
    assert emit(client,sid,'practice_invitation_responded',payload,eid).json()['id']==first.json()['id']
    # A second tab cannot change an already answered invitation or reset cooldown.
    assert emit(client,sid,'practice_invitation_responded',{**payload,'decision':'try_myself'}).json()['id']==first.json()['id']
    data=client.get('/sessions/'+sid).json()
    assert not data['practice']['eligible'] and data['mode']=='ask_ai'
    assert len(learner)==3
    answer(client,sid,4)
    assert len(learner)==4
    assert not client.get('/sessions/'+sid).json()['practice']['eligible']


def test_yes_switches_atomically_without_fabricating_work(client,learner):
    sid,target=ready(client)
    before=client.get('/ai/usage').json()['requests_used']
    eid=uid()
    for _ in range(2):
        assert emit(client,sid,'practice_invitation_responded',dict(answer_event_id=target,decision='try_myself'),eid).status_code==200
    data=client.get('/sessions/'+sid).json()
    assert data['mode']=='try_myself' and data['practice']['active']
    assert data['practice']['question']=='Explain example 2'
    assert 'output' in data['practice']['task']
    assert sum(e['event_type']=='conversation_mode_changed' for e in data['events'])==1
    assert not any(e['event_type'] in ('attempt_submitted','verification_submitted','attempt_skipped') for e in data['events'])
    assert client.get('/ai/usage').json()['requests_used']==before
    assert len(learner)==3
    emit(client,sid,'attempt_submitted',{'attempt_text':'I would trace the loop once.'})
    assert not client.get('/sessions/'+sid).json()['practice']['active']


def test_preferences_persist_across_chats_and_are_owner_scoped(client,learner):
    sid,target=ready(client)
    assert client.get('/preferences').json()=={'practice_reminders':True}
    assert client.post('/preferences',json={'practice_reminders':False}).status_code==200
    assert not client.get('/sessions/'+sid).json()['practice']['eligible']
    assert not client.get('/sessions/'+chat(client)).json()['practice']['reminders_enabled']
    assert emit(client,sid,'practice_invitation_responded',dict(answer_event_id=target,decision='continue_ai')).status_code==409
    original=app.dependency_overrides[identity]
    app.dependency_overrides[identity]=lambda:'other-practice-'+uid()
    assert client.get('/preferences').json()['practice_reminders']
    assert client.get('/sessions/'+sid).status_code==404
    app.dependency_overrides[identity]=original
    assert not client.get('/preferences').json()['practice_reminders']
    assert client.post('/preferences',json={'practice_reminders':'false'}).status_code==422
    assert client.post('/preferences',json={'practice_reminders':True,'user_id':uid()}).status_code==422
    client.post('/preferences',json={'practice_reminders':True})
    assert client.get('/sessions/'+sid).json()['practice']['eligible']


def test_feedback_can_change_and_clear_on_closed_chat_without_changing_metrics(client,learner):
    sid=chat(client)
    target=answer(client,sid)
    client.post('/sessions/'+sid+'/close',json={'event_id':uid(),'final_status':'solved_with_ai'})
    for rating in ('helpful','not_helpful','cleared'):
        eid=uid()
        payload=dict(answer_event_id=target,rating=rating)
        first=emit(client,sid,'answer_feedback',payload,eid)
        assert first.status_code==200,first.text
        assert emit(client,sid,'answer_feedback',payload,eid).json()['id']==first.json()['id']
    data=client.get('/sessions/'+sid).json()
    assert data['status']=='closed' and data['summary']['verification_count']==0
    assert data['summary']['ai_requests']==1 and len(learner)==1
    assert [e['payload']['rating'] for e in data['events'] if e['event_type']=='answer_feedback']==['helpful','not_helpful','cleared']


def test_invalid_anchors_early_decisions_and_legacy_protocol_are_rejected(client,learner):
    sid=chat(client)
    target=answer(client,sid)
    assert not client.get('/sessions/'+sid).json()['practice']['eligible']
    assert emit(client,sid,'practice_invitation_responded',dict(answer_event_id=target,decision='try_myself')).status_code==409
    other=chat(client)
    assert emit(client,other,'answer_feedback',dict(answer_event_id=target,rating='helpful')).status_code==400
    legacy=chat(client,'guided')
    assert not client.get('/sessions/'+legacy).json()['practice']['eligible']
    assert emit(client,legacy,'answer_feedback',dict(answer_event_id=target,rating='helpful')).status_code==409


def test_cooldown_streak_resets_failed_calls_and_max_two_decisions():
    base=datetime(2026,9,16,tzinfo=timezone.utc)
    events=[]
    def add(kind,**payload):
        e=dict(id=uid(),event_type=kind,payload=payload,created_at=base.isoformat())
        events.append(e)
        return e['id']
    add('session_started',experience='chat',problem_domain='math',problem_text='Solve this equation')
    for _ in range(5):add('ai_hint_failed')
    assert not practice.state(events,at=base)['eligible']
    for _ in range(2):add('ai_hint_delivered',mode='ask_ai')
    add('attempt_submitted',attempt_text='My own step')
    add('ai_hint_delivered',mode='ask_ai')
    assert not practice.state(events,at=base)['eligible']
    for _ in range(2):add('ai_hint_delivered',mode='ask_ai')
    target=practice.state(events,at=base)['answer_event_id']
    add('practice_invitation_responded',answer_event_id=target,decision='continue_ai')
    for _ in range(3):add('ai_hint_delivered',mode='ask_ai')
    assert not practice.state(events,at=base+timedelta(minutes=9,seconds=59))['eligible']
    second=practice.state(events,at=base+timedelta(minutes=10))
    assert second['eligible']
    add('practice_invitation_responded',answer_event_id=second['answer_event_id'],decision='continue_ai')
    for _ in range(10):add('ai_hint_delivered',mode='ask_ai')
    assert not practice.state(events,at=base+timedelta(days=1))['eligible']


def test_manual_try_myself_resets_streak(client,learner):
    sid,_=ready(client)
    emit(client,sid,'conversation_mode_changed',{'mode':'try_myself'})
    emit(client,sid,'conversation_mode_changed',{'mode':'ask_ai'})
    assert not client.get('/sessions/'+sid).json()['practice']['eligible']
    answer(client,sid,4)
    assert not client.get('/sessions/'+sid).json()['practice']['eligible']


@pytest.mark.skipif(engine.dialect.name!='postgresql',reason='Production row-lock concurrency check')
def test_concurrent_tabs_record_only_one_practice_decision(client,learner):
    sid,target=ready(client)
    def respond(decision):
        return emit(client,sid,'practice_invitation_responded',dict(answer_event_id=target,decision=decision))
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses=list(executor.map(respond,('try_myself','continue_ai')))
    assert all(response.status_code==200 for response in responses)
    assert responses[0].json()['id']==responses[1].json()['id']
    data=client.get('/sessions/'+sid).json()
    assert sum(e['event_type']=='practice_invitation_responded' for e in data['events'])==1
    assert len(learner)==3
