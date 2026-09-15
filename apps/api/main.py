import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from analytics.etl import effective, reconstruct, summarize, timestamp, user_frame
from analytics.stats import analyze
from . import provider, routing
from .auth import identity, is_admin, mode
from .db import Event, ResearchExport, Rollup, Session, SessionLocal, User, migrate, now
from .schemas import Close, Emit, Hint, PAYLOADS, Start


@asynccontextmanager
async def lifespan(app):
    mode()
    provider.configuration()
    routing.order()
    migrate()
    yield


app = FastAPI(title='ThinkFirst research instrument', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('WEB_ORIGINS', 'http://localhost:3000').split(','),
                   allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    import logging
    logging.getLogger(__name__).exception('Database operation failed', exc_info=exc)
    return JSONResponse(status_code=503, content={'detail': 'The database could not save this operation. Please retry; duplicate events are prevented.'})


def database():
    with SessionLocal() as db:
        yield db


def user(subject=Depends(identity), db=Depends(database)):
    found = db.scalar(select(User).where(User.subject == subject))
    if not found:
        found = User(subject=subject)
        db.add(found)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            found = db.scalar(select(User).where(User.subject == subject))
    return found


def serialize(e):
    return dict(id=e.id, event_id=e.id, user_id=e.user_id, session_id=e.session_id,
                event_type=e.event_type, payload=e.payload, created_at=timestamp(e.created_at).isoformat())


def timeline(db, sid):
    return [serialize(e) for e in db.scalars(select(Event).where(Event.session_id == sid).order_by(Event.created_at, Event.id))]


def locked(db, sid, participant, require_open=True):
    session = db.scalar(select(Session).where(Session.id == str(sid), Session.user_id == participant.id).with_for_update())
    if not session:
        raise HTTPException(404, 'Session not found.')
    if require_open and session.status != 'open':
        raise HTTPException(409, 'This session is already closed.')
    return session


def duplicate(db, eid, participant, sid=None, kind=None):
    e = db.get(Event, str(eid))
    if e and (e.user_id != participant.id or (sid and e.session_id != str(sid)) or (kind and e.event_type != kind)):
        raise HTTPException(409, 'This event ID is already used by another operation.')
    return e


def append(db, session, kind, payload, eid=None):
    previous = db.scalar(select(Event.created_at).where(Event.session_id == session.id).order_by(Event.created_at.desc()).limit(1))
    created = max(now(), timestamp(previous) + timedelta(microseconds=1)) if previous else now()
    event = Event(user_id=session.user_id, session_id=session.id, event_type=kind,
                  payload={**payload, 'session_id': session.id}, created_at=created)
    if eid:
        event.id = str(eid)
    db.add(event)
    db.flush()
    return event


def refresh(db, participant_id):
    events = [serialize(e) for e in db.scalars(select(Event).where(Event.user_id == participant_id))]
    row = db.get(Rollup, participant_id)
    if row is None:
        row = Rollup(user_id=participant_id, data={})
        db.add(row)
    row.data = summarize(reconstruct(events), events)
    row.refreshed_at = now()
    db.flush()
    return row


def commit(db, participant_id):
    # User lock serializes rollup writes across concurrent sessions for a participant.
    db.scalar(select(User).where(User.id == participant_id).with_for_update())
    refresh(db, participant_id)
    db.commit()


def pending_hints(events):
    addressed = {e['payload']['hint_event_id'] for e in events if e['event_type'] in ('verification_submitted', 'verification_skipped')}
    return [e for e in events if e['event_type'] == 'ai_hint_delivered' and e['id'] not in addressed]


def in_flight(events):
    finished = {e['payload'].get('request_event_id') for e in events if e['event_type'] in ('ai_hint_delivered', 'ai_hint_failed')}
    return [e for e in events if e['event_type'] == 'ai_hint_requested' and e['id'] not in finished]


def currently_evaluated(events):
    decisions = [e for e in events if e['event_type'] in ('ai_hint_delivered', 'evaluation_submitted', 'evaluation_skipped')]
    return bool(decisions and decisions[-1]['event_type'].startswith('evaluation_'))


def expire_interrupted(db, session, events):
    for pending in in_flight(events):
        if (now()-timestamp(pending['created_at'])).total_seconds() >= 90:
            append(db, session, 'ai_hint_failed', {**{key: pending['payload'][key] for key in ('provider', 'model') if key in pending['payload']}, 'request_event_id': pending['id'], 'reason': 'Request interrupted. Please request a new hint.'})
    return effective(timeline(db, session.id))


@app.get('/health')
def health(db=Depends(database)):
    db.execute(select(1))
    return {'status': 'ok', 'database': 'connected', 'auth_mode': mode()}


@app.get('/me')
def me(participant=Depends(user)):
    return {'id': participant.id, 'display_name': participant.display_name,
            'admin': is_admin(participant.subject), 'development': mode() == 'development'}


@app.get('/ai/status')
def ai_status(participant=Depends(user)):
    # Report configuration only. Never expose the secret or imply a live call succeeded.
    return provider.status()


@app.post('/sessions', status_code=201)
def start(body: Start, db=Depends(database), participant=Depends(user)):
    db.scalar(select(User).where(User.id == participant.id).with_for_update())
    old = duplicate(db, body.event_id, participant, kind='session_started')
    if old:
        if old.payload['problem_text'] != body.problem_text or old.payload['problem_domain'] != body.problem_domain:
            raise HTTPException(409, 'Event ID reused with different problem data.')
        return {'id': old.session_id}
    s = Session(user_id=participant.id, problem_domain=body.problem_domain)
    db.add(s)
    db.flush()
    append(db, s, 'session_started', {'problem_domain': body.problem_domain, 'problem_text': body.problem_text,
                                    'created_at': timestamp(s.started_at).isoformat()}, body.event_id)
    commit(db, participant.id)
    return {'id': s.id}


@app.get('/sessions')
def sessions(db=Depends(database), participant=Depends(user)):
    result = []
    for s in db.scalars(select(Session).where(Session.user_id == participant.id).order_by(Session.started_at.desc()).limit(100)):
        start = db.scalar(select(Event).where(Event.session_id == s.id, Event.event_type == 'session_started'))
        result.append({'id': s.id, 'domain': s.problem_domain, 'status': s.status,
                       'started_at': timestamp(s.started_at).isoformat(), 'problem_text': start.payload['problem_text']})
    return result


@app.get('/sessions/{sid}')
def get_session(sid: UUID, db=Depends(database), participant=Depends(user)):
    s = locked(db, sid, participant, False)
    events = timeline(db, s.id)
    return {'id': s.id, 'status': s.status, 'events': effective(events), 'summary': reconstruct(events)[0]}


@app.post('/events')
def emit(body: Emit, db=Depends(database), participant=Depends(user)):
    if body.event_type not in PAYLOADS:
        raise HTTPException(400, 'Unknown or server-owned event type.')
    try:
        payload = PAYLOADS[body.event_type].model_validate(body.payload).model_dump(mode='json')
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    s = locked(db, body.session_id, participant, False)
    old = duplicate(db, body.event_id, participant, s.id, body.event_type)
    if old:
        if any(old.payload.get(k) != v for k, v in payload.items()):
            raise HTTPException(409, 'Event ID reused with different data.')
        return serialize(old)
    if s.status != 'open':
        raise HTTPException(409, 'This session is closed. The pending event has not been saved.')
    events = effective(timeline(db, s.id))
    kind = body.event_type
    if kind in ('attempt_submitted', 'attempt_skipped'):
        payload['time_since_session_start_ms'] = int((now()-timestamp(s.started_at)).total_seconds()*1000)
        if kind == 'attempt_submitted':
            payload['text_length'] = len(payload['attempt_text'])
    if kind.startswith('verification_'):
        target = next((e for e in pending_hints(events) if e['id'] == payload['hint_event_id']), None)
        if not target:
            raise HTTPException(409, 'This hint is missing or already has a verification decision.')
        if kind == 'verification_submitted':
            payload['time_since_hint_delivered_ms'] = int((now()-timestamp(target['created_at'])).total_seconds()*1000)
    if kind.startswith('evaluation_'):
        if not any(e['event_type'] == 'ai_hint_delivered' for e in events):
            raise HTTPException(409, 'Evaluation needs a delivered AI response.')
        if in_flight(events):
            raise HTTPException(409, 'Wait for the current AI response before evaluating it.')
        if currently_evaluated(events):
            raise HTTPException(409, 'An evaluation decision is already saved.')
    if kind == 'attempt_correctness_reported':
        if not any(e['id'] == payload['attempt_event_id'] and e['event_type'] == 'attempt_submitted' for e in events):
            raise HTTPException(400, 'Correctness must reference an attempt from this session.')
    if kind == 'event_invalidated':
        if not is_admin(participant.subject):
            raise HTTPException(403, 'Research administrator access required.')
        target = next((e for e in events if e['id'] == payload['target_event_id']), None)
        if not target or target['event_type'] in ('session_started', 'session_closed', 'event_invalidated'):
            raise HTTPException(400, 'Invalid correction target.')
    e = append(db, s, kind, payload, body.event_id)
    commit(db, participant.id)
    return serialize(e)


@app.post('/sessions/{sid}/close')
def close(sid: UUID, body: Close, db=Depends(database), participant=Depends(user)):
    s = locked(db, sid, participant, False)
    old = duplicate(db, body.event_id, participant, s.id, 'session_closed')
    if old:
        if old.payload['final_status'] != body.final_status:
            raise HTTPException(409, 'Event ID reused with different closure data.')
        return serialize(old)
    if s.status != 'open':
        raise HTTPException(409, 'This session is already closed.')
    events = effective(timeline(db, s.id))
    events = expire_interrupted(db, s, events)
    if in_flight(events):
        raise HTTPException(409, 'An AI request is still pending. Wait for its result before closing.')
    count = sum(e['event_type'] == 'ai_hint_requested' for e in events)
    if body.final_status == 'solved_independently' and count:
        raise HTTPException(409, 'This session includes AI requests; choose solved with AI or leave unfinished.')
    if body.final_status == 'solved_without_ai_response' and (not count or any(e['event_type'] == 'ai_hint_delivered' for e in events)):
        raise HTTPException(409, 'This outcome requires an AI request with no delivered response.')
    if body.final_status == 'solved_with_ai':
        if not any(e['event_type'] == 'ai_hint_delivered' for e in events):
            raise HTTPException(409, 'No AI response was delivered.')
        if pending_hints(events) or not currently_evaluated(events):
            raise HTTPException(409, 'Complete or explicitly skip verification and evaluation before finishing.')
    s.status, s.closed_at = 'closed', now()
    e = append(db, s, 'session_closed', {'final_status': body.final_status, 'ai_events_count': count,
                                       'total_duration_ms': int((s.closed_at-timestamp(s.started_at)).total_seconds()*1000)}, body.event_id)
    commit(db, participant.id)
    return serialize(e)


@app.post('/ai/hint')
def hint(body: Hint, db=Depends(database), participant=Depends(user)):
    s = locked(db, body.session_id, participant, False)
    events = effective(timeline(db, s.id))
    old = duplicate(db, body.event_id, participant, s.id, 'ai_hint_requested')
    if old:
        if old.payload['tier_requested'] != body.tier:
            raise HTTPException(409, 'Event ID reused with a different tier.')
        if body.followup_text != old.payload.get('followup_text'):
            raise HTTPException(409, 'Event ID reused with a different question.')
        if body.provider and body.provider != old.payload.get('selected_provider', old.payload.get('provider', 'anthropic')):
            raise HTTPException(409, 'Event ID reused with a different provider. Finish checking the pending request first.')
        if any(e['id'] == old.id for e in in_flight(events)) and (now()-timestamp(old.created_at)).total_seconds() >= 90:
            events = expire_interrupted(db, s, events)
            commit(db, participant.id)
        result = next((e for e in events if e['event_type'] in ('ai_hint_delivered', 'ai_hint_failed') and e['payload'].get('request_event_id') == old.id), None)
        if result and result['event_type'] == 'ai_hint_delivered':
            return result
        if result:
            raise HTTPException(502, result['payload']['reason'])
        raise HTTPException(409, 'This request is still pending. Refresh the session to check its status.')
    if s.status != 'open':
        raise HTTPException(409, 'This session is closed.')
    events = expire_interrupted(db, s, events)
    if in_flight(events):
        raise HTTPException(409, 'Another hint is already being requested.')
    if not any(e['event_type'] in ('attempt_submitted', 'attempt_skipped') for e in events):
        raise HTTPException(409, 'Save an attempt or explicitly skip it first.')
    delivered = [e for e in events if e['event_type'] == 'ai_hint_delivered']
    expected = min(len(delivered)+1, 3)
    if body.followup_text and (body.tier != 3 or not any(e['payload']['tier'] == 3 for e in delivered)):
        raise HTTPException(409, 'Follow-up questions are available after the full explanation.')
    if body.tier != expected or (len(delivered) >= 3 and not body.followup_text):
        raise HTTPException(409, 'Request the next available hint level.')
    if pending_hints(events):
        raise HTTPException(409, 'Verify or explicitly skip the previous hint first.')
    attempts = [e for e in events if e['event_type'] == 'attempt_submitted']
    config = provider.configuration(body.provider)
    provenance = {'provider': config['id'], 'model': config['model']}
    req = append(db, s, 'ai_hint_requested', {**provenance, 'selected_provider': body.provider,
                                            'request_kind': 'followup' if body.followup_text else 'hint', 'followup_text': body.followup_text,
                                            'fallback_enabled': routing.enabled(), 'tier_requested': body.tier, 'preceded_by_attempt': bool(attempts),
                                            'time_since_session_start_ms': int((now()-timestamp(s.started_at)).total_seconds()*1000)}, body.event_id)
    commit(db, participant.id)  # Persist request before contacting provider, including on failure.
    request_id = req.id
    db.commit()  # Reading an expired ORM object may start a transaction; release it before network I/O.
    def record_attempt(report):
        session = locked(db, body.session_id, participant)
        report = dict(report)
        violation = report.pop('violation_response', None)
        append(db, session, 'ai_provider_attempted', {**report, 'request_event_id': request_id})
        if violation is not None:
            append(db, session, 'hint_tier_violation', {'request_event_id': request_id, 'provider': report['provider'],
                   'model': report['model'], 'tier': body.tier, 'reason': 'Response exceeded hint level.', 'provider_response': violation})
        db.commit()
    conversation = []
    for event in events:
        if event['event_type'] == 'ai_hint_delivered':
            if event['payload'].get('followup_text'):
                conversation.append({'role': 'user', 'content': event['payload']['followup_text']})
            conversation.append({'role': 'assistant', 'content': event['payload']['hint_text']})
    began = time.monotonic()
    try:
        generation = routing.generate(body.tier, events[0]['payload']['problem_text'],
                                 attempts[-1]['payload']['attempt_text'] if attempts else '',
                                 [e['payload']['hint_text'] for e in delivered], body.provider,
                                 conversation, body.followup_text, record_attempt)
    except SQLAlchemyError:
        raise
    except Exception as exc:
        s = locked(db, body.session_id, participant)
        if isinstance(exc, provider.TierViolation):
            append(db, s, 'hint_tier_violation', {**provenance, 'tier': body.tier, 'reason': str(exc), 'provider_response': exc.response})
        reason = str(exc) if isinstance(exc, (ValueError, provider.TierViolation)) else 'AI assistance could not connect. Your work is saved. Try again when ready.'
        append(db, s, 'ai_hint_failed', {**provenance, 'request_event_id': request_id, 'reason': reason})
        commit(db, participant.id)
        raise HTTPException(502, reason) from exc
    s = locked(db, body.session_id, participant)
    if not any(e['id'] == request_id for e in in_flight(effective(timeline(db, s.id)))):
        raise HTTPException(409, 'This request has already finished. Retrieve its saved result.')
    result = append(db, s, 'ai_hint_delivered', {'provider': generation.provider or config['id'], 'model': generation.model or config['model'],
                                               'request_kind': 'followup' if body.followup_text else 'hint', 'followup_text': body.followup_text,
                                               'reported_model': generation.reported_model, 'tier': body.tier, 'hint_text': generation.text, 'request_event_id': request_id,
                                               'model_latency_ms': int((time.monotonic()-began)*1000)})
    commit(db, participant.id)
    return serialize(result)


@app.get('/ai/requests/{event_id}')
def request_status(event_id: UUID, db=Depends(database), participant=Depends(user)):
    request = db.get(Event, str(event_id))
    if not request or request.user_id != participant.id or request.event_type != 'ai_hint_requested':
        raise HTTPException(404, 'AI request not found.')
    session = locked(db, request.session_id, participant, False)
    events = expire_interrupted(db, session, effective(timeline(db, session.id)))
    result = next((e for e in events if e['event_type'] in ('ai_hint_delivered', 'ai_hint_failed') and e['payload'].get('request_event_id') == str(event_id)), None)
    commit(db, participant.id)
    return {'status': 'pending' if result is None else 'delivered' if result['event_type'] == 'ai_hint_delivered' else 'failed', 'result': result}


@app.get('/analytics/me')
def personal(db=Depends(database), participant=Depends(user)):
    db.scalar(select(User).where(User.id == participant.id).with_for_update())
    row = db.get(Rollup, participant.id)
    if row is None or now()-timestamp(row.refreshed_at) > timedelta(minutes=5):
        row = refresh(db, participant.id)
    db.commit()
    return {**row.data, 'refreshed_at': timestamp(row.refreshed_at).isoformat()}


@app.get('/analytics/research')
def research(start: datetime | None = None, end: datetime | None = None, format: str = 'json',
             db=Depends(database), participant=Depends(user)):
    if not is_admin(participant.subject):
        raise HTTPException(403, 'Research administrator access required.')
    if format not in ('json', 'csv'):
        raise HTTPException(400, 'Format must be json or csv.')
    if start and end and timestamp(start) > timestamp(end):
        raise HTTPException(400, 'Start must precede end.')
    events = [serialize(e) for e in db.scalars(select(Event))]
    rows = reconstruct(events)  # Reconstruct complete timelines before applying date filters.
    rows = [r for r in rows if not r.get('excluded') and
            (not start or timestamp(r['started_at']) >= timestamp(start)) and
            (not end or timestamp(r['started_at']) <= timestamp(end))]
    frame = user_frame(rows)
    if format == 'csv':
        return Response(frame.to_csv(index=False), media_type='text/csv',
                        headers={'Content-Disposition': 'attachment; filename="thinkfirst-participants.csv"'})
    output = analyze(frame)
    output['refreshed_at'] = now().isoformat()
    output['session_count'] = len(rows)
    db.add(ResearchExport(data=output))
    db.commit()
    return output
