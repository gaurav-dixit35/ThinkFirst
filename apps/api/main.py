import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from analytics.etl import effective, reconstruct, summarize, timestamp, user_frame
from analytics.stats import analyze
from . import provider, routing, usage, practice, activity, privacy, chat_context, deployment, learning, workspace, question_tracking
from .http_safety import RequestBodyLimit
from .auth import identity, is_admin, mode, origins, validate_configuration
from .db import Event, ResearchExport, Rollup, Session, SessionLocal, User, UserPreferences, UserPrivacy, DeletionRequest, ConversationMetadata, AnswerPreferences, ResponseDraft, ConversationState, ConversationDeletion, LearningPreferences, SupportReport, migrate, verify_schema, now
from .schemas import Close, Emit, Hint, PAYLOADS, Start, Preferences, ConversationTitle, AnalysisRequest, PrivacyChoices, DeleteConversations, AnswerPreference, ArchiveConversation, DeleteConversation, EditQuestion, LanguagePreference, LearningGoal, ReportProblem, ReportStatus


@asynccontextmanager
async def lifespan(app):
    validate_configuration()
    provider.configuration()
    routing.order()
    usage.limits()
    deployment.public_info()
    if deployment.auto_migrate():
        migrate()
    else:
        verify_schema()
        if os.getenv('ENVIRONMENT', 'production') != 'development':
            from .db import engine
            from .permissions import verify_runtime
            if engine.dialect.name != 'postgresql':
                raise RuntimeError('Production requires PostgreSQL.')
            with engine.connect() as connection:
                verify_runtime(connection)
    yield


app = FastAPI(title='ThinkFirst API', version='1.0.0', lifespan=lifespan)
app.add_middleware(RequestBodyLimit)
app.add_middleware(CORSMiddleware, allow_origins=origins(),
                   allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'], expose_headers=['X-Request-ID'])


@app.middleware('http')
async def private_responses(request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as exc:
        logging.getLogger('uvicorn.error').error('request_failed request_id=%s exception=%s', request_id, type(exc).__name__)
        response = JSONResponse({'detail': 'Something went wrong. Please retry, or contact support with this request reference.'}, status_code=500)
        if request.headers.get('origin') in origins():
            response.headers['Access-Control-Allow-Origin'] = request.headers['origin']
            response.headers['Access-Control-Expose-Headers'] = 'X-Request-ID'
            response.headers['Vary'] = 'Origin'
    route = getattr(request.scope.get('route'), 'path', '<unmatched>')
    logging.getLogger('uvicorn.error').info('request_complete request_id=%s method=%s route=%s status=%s duration_ms=%d',
        request_id, request.method, route, response.status_code, int((time.monotonic()-started)*1000))
    response.headers['X-Request-ID'] = request_id
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


@app.get('/service-info')
def service_info():
    return deployment.public_info()


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    import logging
    # SQL exception strings can contain private text in query parameters.
    logging.getLogger('uvicorn.error').error('database_error request_id=%s exception=%s', request.state.request_id, type(exc).__name__)
    return JSONResponse(status_code=503, content={'detail': 'The database could not save this operation. Please retry; duplicate events are prevented.'})


def database():
    with SessionLocal() as db:
        yield db


def user(request: Request, subject=Depends(identity), db=Depends(database)):
    found = db.scalar(select(User).where(User.subject == subject))
    if not found:
        found = User(subject=subject)
        db.add(found)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            found = db.scalar(select(User).where(User.subject == subject))
    if request.method == 'POST' and not request.url.path.startswith('/privacy') and not request.url.path.endswith('/cancel'):
        if privacy.pending(db, found.id):
            raise HTTPException(409, 'Conversation deletion is pending. You can still read and export your data in Settings.')
        if mode() != 'development' and not privacy.state(db, found.id)['acknowledged']:
            raise HTTPException(428, 'Please read and acknowledge the data notice before saving work.')
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
    if require_open and db.scalar(select(ConversationDeletion.id).where(ConversationDeletion.session_id==session.id, ConversationDeletion.status=='pending')):
        raise HTTPException(409, 'Conversation deletion is pending. You can still read or export it.')
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


def conversation_settings(events):
    start = next(e for e in events if e['event_type'] == 'session_started')
    changes = [e for e in events if e['event_type'] == 'conversation_mode_changed']
    return {'experience': start['payload'].get('experience', 'guided'),
            'mode': changes[-1]['payload']['mode'] if changes else start['payload'].get('initial_mode', 'ask_ai')}


def expire_interrupted(db, session, events):
    for pending in in_flight(events):
        if (now()-timestamp(pending['created_at'])).total_seconds() >= 90:
            draft=db.get(ResponseDraft,pending['id'])
            if draft: draft.text=''
            append(db, session, 'ai_hint_failed', {**{key: pending['payload'][key] for key in ('provider', 'model') if key in pending['payload']}, 'request_event_id': pending['id'], 'reason': 'Request interrupted. Please request a new hint.'})
    return effective(timeline(db, session.id))


@app.get('/health')
def health(db=Depends(database)):
    db.execute(select(1))
    return {'status': 'ok', 'database': 'connected', 'auth_mode': mode()}


@app.get('/operator/status')
def operator_status(db=Depends(database), participant=Depends(user)):
    if mode() != 'development' and not is_admin(participant.subject):
        raise HTTPException(403, 'Operator access required.')
    return {'auth_mode': mode(), 'database': 'connected', 'privacy_notice_version': privacy.NOTICE_VERSION,
            'deletion_requests': [privacy.record(r) for r in db.scalars(select(DeletionRequest).where(DeletionRequest.status == 'pending').order_by(DeletionRequest.created_at))] + [privacy.record(r) for r in db.scalars(select(ConversationDeletion).where(ConversationDeletion.status=='pending').order_by(ConversationDeletion.created_at))]}


@app.get('/me')
def me(db=Depends(database), participant=Depends(user)):
    return {'id': participant.id, 'display_name': participant.display_name,
            'admin': is_admin(participant.subject), 'development': mode() == 'development',
            'privacy': privacy.state(db, participant.id)}


@app.get('/privacy')
def privacy_status(db=Depends(database), participant=Depends(user)):
    return privacy.state(db, participant.id)


@app.post('/privacy')
def privacy_choices(body: PrivacyChoices, db=Depends(database), participant=Depends(user)):
    db.scalar(select(User).where(User.id == participant.id).with_for_update())
    if body.research_opt_in and privacy.pending(db, participant.id):
        raise HTTPException(409, 'Research sharing stays off while deletion is pending.')
    row = db.get(UserPrivacy, participant.id)
    if not row:
        row = UserPrivacy(user_id=participant.id)
        db.add(row)
    row.research_opt_in = body.research_opt_in
    row.updated_at = now()
    if body.acknowledge_notice:
        row.notice_version = privacy.NOTICE_VERSION
        row.acknowledged_at = now()
    db.commit()
    return privacy.state(db, participant.id)


@app.get('/privacy/export')
def export_my_data(db=Depends(database), participant=Depends(user)):
    return JSONResponse(jsonable_encoder(privacy.export_account(db, participant)),
                        headers={'Content-Disposition': 'attachment; filename="thinkfirst-my-data.json"'})


@app.post('/privacy/deletion', status_code=202)
def request_deletion(body: DeleteConversations, db=Depends(database), participant=Depends(user)):
    db.scalar(select(User).where(User.id == participant.id).with_for_update())
    if not privacy.pending(db, participant.id):
        db.add(DeletionRequest(user_id=participant.id))
    row = db.get(UserPrivacy, participant.id)
    if row:
        row.research_opt_in = False
        row.updated_at = now()
    db.commit()
    return privacy.state(db, participant.id)


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
        if old.payload.get('experience', 'guided') != body.experience or old.payload.get('initial_mode', 'ask_ai') != body.initial_mode:
            raise HTTPException(409, 'Event ID reused with different conversation settings.')
        return {'id': old.session_id}
    s = Session(user_id=participant.id, problem_domain=body.problem_domain)
    db.add(s)
    db.flush()
    append(db, s, 'session_started', {'problem_domain': body.problem_domain, 'problem_text': body.problem_text,
                                    'experience': body.experience, 'initial_mode': body.initial_mode,
                                    'protocol_version': 'chat-v1' if body.experience == 'chat' else 'guided-v1',
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


@app.get('/preferences')
def get_preferences(db=Depends(database), participant=Depends(user)):
    return practice.preferences(db, participant.id)


@app.get('/preferences/answers')
def answer_preferences(db=Depends(database), participant=Depends(user)):
    row = db.get(AnswerPreferences, participant.id)
    return {'answer_style': row.answer_style if row else 'concise'}


@app.post('/preferences/answers')
def save_answer_preferences(body: AnswerPreference, db=Depends(database), participant=Depends(user)):
    db.scalar(select(User).where(User.id == participant.id).with_for_update())
    row = db.get(AnswerPreferences, participant.id)
    if row is None:
        row = AnswerPreferences(user_id=participant.id)
        db.add(row)
    row.answer_style = body.answer_style
    db.commit()
    return {'answer_style': row.answer_style}


def learning_preferences_row(db, participant):
    db.scalar(select(User).where(User.id==participant.id).with_for_update())
    row = db.get(LearningPreferences, participant.id)
    if row is None:
        row = LearningPreferences(user_id=participant.id)
        db.add(row)
    return row


@app.get('/preferences/language')
def get_language(db=Depends(database), participant=Depends(user)):
    return {'answer_language':workspace.preferences(db,participant.id)['answer_language']}


@app.post('/preferences/language')
def save_language(body: LanguagePreference, db=Depends(database), participant=Depends(user)):
    row = learning_preferences_row(db,participant)
    row.answer_language = body.answer_language
    db.commit()
    return {'answer_language':row.answer_language}


@app.get('/learning-goal')
def get_learning_goal(db=Depends(database), participant=Depends(user)):
    return workspace.goal_progress(db,participant.id)


@app.post('/learning-goal')
def save_learning_goal(body: LearningGoal, db=Depends(database), participant=Depends(user)):
    if body.weekly_target and not body.goal:
        raise HTTPException(422, 'Give your goal a short name, or set the target to zero to pause it.')
    row = learning_preferences_row(db,participant)
    row.goal, row.weekly_target = body.goal, body.weekly_target
    db.commit()
    return workspace.goal_progress(db,participant.id)


@app.get('/support/reports')
def own_reports(db=Depends(database), participant=Depends(user)):
    return [privacy.record(row) for row in db.scalars(select(SupportReport).where(SupportReport.user_id==participant.id).order_by(SupportReport.created_at.desc(),SupportReport.id).limit(20))]


@app.post('/support/reports', status_code=201)
def report_problem(body: ReportProblem, db=Depends(database), participant=Depends(user)):
    db.scalar(select(User).where(User.id==participant.id).with_for_update())
    reference = str(body.reference) if body.reference else None
    old = db.get(SupportReport, str(body.id))
    if old:
        if old.user_id!=participant.id or old.category!=body.category or old.message!=body.message or old.reference!=reference:
            raise HTTPException(409, 'This report reference is already in use.')
        return privacy.record(old)
    recent = list(db.scalars(select(SupportReport.id).where(SupportReport.user_id==participant.id, SupportReport.created_at>=now()-timedelta(days=1)).limit(10)))
    if len(recent)>=10:
        raise HTTPException(429, 'You can submit up to 10 reports in 24 hours. Please wait before sending another.')
    row = SupportReport(id=str(body.id),user_id=participant.id,category=body.category,message=body.message,reference=reference)
    db.add(row)
    db.commit()
    return privacy.record(row)


def require_operator(participant):
    if mode()!='development' and not is_admin(participant.subject):
        raise HTTPException(403, 'Operator access required.')


@app.get('/operator/reports')
def operator_reports(status: Literal['open','resolved']='open', offset: int=Query(0,ge=0), db=Depends(database), participant=Depends(user)):
    require_operator(participant)
    rows = list(db.scalars(select(SupportReport).where(SupportReport.status==status).order_by(SupportReport.created_at,SupportReport.id).offset(offset).limit(26)))
    return {'items':[privacy.record(row) for row in rows[:25]], 'has_more':len(rows)>25}


@app.post('/operator/reports/{report_id}')
def update_report(report_id: UUID, body: ReportStatus, db=Depends(database), participant=Depends(user)):
    require_operator(participant)
    row = db.scalar(select(SupportReport).where(SupportReport.id==str(report_id)).with_for_update())
    if row is None:
        raise HTTPException(404, 'Report not found.')
    row.status, row.updated_at = body.status, now()
    db.commit()
    return privacy.record(row)


@app.get('/history')
def history(q: str = Query('', max_length=200), status: Literal['all','open','completed','abandoned'] = 'all',
            experience: Literal['all','chat','guided'] = 'all', limit: int = Query(25,ge=1,le=50),
            offset: int = Query(0,ge=0), folder: Literal['active','archived','deletion']='active', db=Depends(database), participant=Depends(user)):
    return activity.history(db,participant.id,q,status,experience,limit,offset,folder)


@app.get('/saved')
def saved_answers(q: str = Query('', max_length=200), unpractised: bool = False,
                  limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0),
                  db=Depends(database), participant=Depends(user)):
    items = learning.library(db, participant.id)
    summary = {'saved':len(items), 'retried':sum(bool(item['attempts']) for item in items),
               'attempts':sum(len(item['attempts']) for item in items)}
    term = q.strip().casefold()
    matches = [item for item in items if (not unpractised or not item['attempts'])
               and (not term or term in item['question'].casefold() or term in item['answer'].casefold())]
    return {'items':[{k:v for k,v in item.items() if k not in ('answer','attempts')} |
                      {'attempt_count':len(item['attempts'])} for item in matches[offset:offset+limit]],
            'total':len(matches), 'has_more':offset+limit<len(matches), 'summary':summary}


@app.get('/saved/{answer_id}')
def saved_answer(answer_id: UUID, db=Depends(database), participant=Depends(user)):
    item = next((item for item in learning.library(db, participant.id) if item['answer_id']==str(answer_id)), None)
    if item is None:
        raise HTTPException(404, 'Saved answer not found. It may have been removed or its conversation deleted.')
    return item


@app.get('/progress')
def progress(experience: Literal['chat','guided'] = 'chat', db=Depends(database), participant=Depends(user)):
    events=[serialize(e) for e in db.scalars(select(Event).where(Event.user_id==participant.id))]
    return activity.progress(events,experience)


@app.post('/sessions/{sid}/title')
def rename(sid: UUID, body: ConversationTitle, db=Depends(database), participant=Depends(user)):
    session=locked(db,sid,participant,False)
    if db.scalar(select(ConversationDeletion.id).where(ConversationDeletion.session_id==session.id,ConversationDeletion.status=='pending')):
        raise HTTPException(409, 'Conversation deletion is pending.')
    metadata=db.get(ConversationMetadata,session.id)
    if metadata is None:
        metadata=ConversationMetadata(session_id=session.id)
        db.add(metadata)
    metadata.title=body.title
    db.commit()
    return {'title':body.title,'custom_title':body.title is not None}


@app.post('/sessions/{sid}/archive')
def archive_conversation(sid: UUID, body: ArchiveConversation, db=Depends(database), participant=Depends(user)):
    session = locked(db, sid, participant, False)
    row = db.get(ConversationState, session.id)
    if row is None:
        row = ConversationState(session_id=session.id)
        db.add(row)
    row.archived = body.archived
    db.commit()
    return {'archived':row.archived}


@app.post('/sessions/{sid}/deletion', status_code=202)
def delete_conversation(sid: UUID, body: DeleteConversation, db=Depends(database), participant=Depends(user)):
    session = locked(db, sid, participant, False)
    row = db.scalar(select(ConversationDeletion).where(ConversationDeletion.session_id==session.id))
    if row:
        return privacy.record(row)
    events = effective(timeline(db,session.id))
    if in_flight(events) or any(e['event_type']=='ai_analysis_requested' and not analysis_result(events,e['id']) for e in events):
        raise HTTPException(409, 'Finish or stop the pending AI response before requesting deletion.')
    row = ConversationDeletion(user_id=participant.id, session_id=session.id)
    db.add(row)
    db.commit()
    return privacy.record(row)


@app.post('/sessions/{sid}/edit-question', status_code=201)
def edit_question(sid: UUID, body: EditQuestion, db=Depends(database), participant=Depends(user)):
    original = locked(db, sid, participant, False)
    if db.scalar(select(ConversationDeletion.id).where(ConversationDeletion.session_id==original.id,ConversationDeletion.status=='pending')):
        raise HTTPException(409, 'This conversation is awaiting deletion.')
    old = db.get(Event,str(body.event_id))
    if old:
        if old.user_id!=participant.id or old.event_type!='session_started' or old.payload.get('edited_from')!={'session_id':str(sid),'event_id':str(body.source_event_id)} or old.payload['problem_text']!=body.question.strip():
            raise HTTPException(409, 'This edit request ID was already used.')
        return {'id':old.session_id}
    events = effective(timeline(db,original.id))
    if conversation_settings(events)['experience']!='chat':
        raise HTTPException(409, 'Editing questions is available in everyday chats.')
    source = next((e for e in events if e['id']==str(body.source_event_id)),None)
    if not source or not (source['event_type']=='session_started' or source['event_type']=='ai_hint_requested' and source['payload'].get('followup_text') and not source['payload'].get('help_action') and not source['payload'].get('regenerate_of')):
        raise HTTPException(422, 'Choose a question you wrote.')
    if not body.question.strip():
        raise HTTPException(422, 'Write a question first.')
    before = events[:events.index(source)]
    context = chat_context.context(before)[2] if before else events[0]['payload'].get('branch_context',[])
    bounded, remaining = [], 24000
    for message in reversed(context[-12:]):
        content = message['content'][-remaining:]
        bounded.insert(0,{'role':message['role'],'content':content})
        remaining -= len(content)
        if not remaining: break
    session = Session(user_id=participant.id,problem_domain=original.problem_domain)
    db.add(session)
    db.flush()
    append(db,session,'session_started',{'problem_text':body.question.strip(),'problem_domain':session.problem_domain,
        'experience':'chat','protocol_version':'chat-v1','initial_mode':'ask_ai','branch_context':bounded,
        'edited_from':{'session_id':str(sid),'event_id':str(body.source_event_id)}},body.event_id)
    commit(db,participant.id)
    return {'id':session.id}


@app.post('/preferences')
def save_preferences(body: Preferences, db=Depends(database), participant=Depends(user)):
    db.scalar(select(User).where(User.id == participant.id).with_for_update())
    row = db.get(UserPreferences, participant.id)
    if row is None:
        row = UserPreferences(user_id=participant.id)
        db.add(row)
    row.practice_reminders = body.practice_reminders
    db.commit()
    return practice.preferences(db, participant.id)


@app.get('/sessions/{sid}')
def get_session(sid: UUID, db=Depends(database), participant=Depends(user)):
    s = locked(db, sid, participant, False)
    events = timeline(db, s.id)
    metadata=db.get(ConversationMetadata,s.id)
    return {'id': s.id, 'status': s.status, 'events': effective(events), 'summary': reconstruct(events)[0],
            'archived':bool((db.get(ConversationState,s.id) or ConversationState()).archived),
            'deletion_pending':bool(db.scalar(select(ConversationDeletion.id).where(ConversationDeletion.session_id==s.id,ConversationDeletion.status=='pending'))),
            'answer_style': answer_preferences(db, participant)['answer_style'],
            **conversation_settings(effective(events)),
            'question_tracking': question_tracking.view(effective(events)) if conversation_settings(effective(events))['experience'] == 'chat' else None,
            'title':metadata.title if metadata and metadata.title else activity.title(events[0]['payload']['problem_text']),
            'custom_title':bool(metadata and metadata.title),'overview':activity.overview(effective(events)),
            'practice': practice.state(effective(events), practice.preferences(db, participant.id)['practice_reminders'], s.status != 'open')}


@app.post('/events')
def emit(body: Emit, db=Depends(database), participant=Depends(user)):
    if body.event_type not in PAYLOADS:
        raise HTTPException(400, 'Unknown or server-owned event type.')
    try:
        payload = PAYLOADS[body.event_type].model_validate(body.payload).model_dump(mode='json')
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    if payload.get('question_event_id') is None:
        payload.pop('question_event_id', None)
    s = locked(db, body.session_id, participant, False)
    old = duplicate(db, body.event_id, participant, s.id, body.event_type)
    if old:
        if any(old.payload.get(k) != v for k, v in payload.items()):
            raise HTTPException(409, 'Event ID reused with different data.')
        return serialize(old)
    if db.scalar(select(ConversationDeletion.id).where(ConversationDeletion.session_id==s.id,ConversationDeletion.status=='pending')):
        raise HTTPException(409,'Conversation deletion is pending.')
    if s.status != 'open' and body.event_type not in ('answer_feedback', 'answer_saved', 'learning_attempt_submitted', 'answer_verification_reported'):
        raise HTTPException(409, 'This session is closed. The pending event has not been saved.')
    events = effective(timeline(db, s.id))
    kind = body.event_type
    if kind in ('practice_invitation_responded', 'answer_feedback', 'answer_saved', 'learning_attempt_submitted', 'answer_verification_reported'):
        if conversation_settings(events)['experience'] != 'chat':
            raise HTTPException(409, 'Optional practice and feedback are available in everyday conversations.')
        if not any(e['id'] == payload['answer_event_id'] and e['event_type'] == 'ai_hint_delivered' for e in events):
            raise HTTPException(400, 'Choose a delivered answer from this conversation.')
    if kind == 'answer_verification_reported':
        target = next(e for e in events if e['id'] == payload['answer_event_id'])
        if target['payload'].get('help_action') == 'exercise':
            raise HTTPException(422, 'Choose an answer rather than a practice question.')
        if (payload['status'] == 'not_checked') != (payload['method'] is None):
            raise HTTPException(422, 'Choose how you checked the answer, or select Not checked without a method.')
        anchor = question_tracking.view(events)['event_questions'].get(target['id'])
        if not anchor:
            raise HTTPException(409, 'The source question is no longer available for verification.')
        payload.update(question_tracking.metadata(anchor))
    if kind == 'learning_attempt_submitted' and not learning.saved_state(events).get(payload['answer_event_id']):
        raise HTTPException(409, 'Save this answer before retrying its question.')
    if kind == 'practice_invitation_responded':
        existing = next((e for e in events if e['event_type'] == kind and e['payload']['answer_event_id'] == payload['answer_event_id']), None)
        if existing:
            # Another tab may already have answered this invitation. First decision wins.
            return existing
        current = practice.state(events, practice.preferences(db, participant.id)['practice_reminders'])
        if not current['eligible'] or current['answer_event_id'] != payload['answer_event_id']:
            raise HTTPException(409, 'This practice invitation is no longer available. You can always choose Try myself.')
    if kind == 'conversation_mode_changed' and conversation_settings(events)['experience'] != 'chat':
        raise HTTPException(409, 'Mode switching is available in everyday conversations.')
    if kind in ('attempt_submitted', 'attempt_skipped'):
        payload['time_since_session_start_ms'] = int((now()-timestamp(s.started_at)).total_seconds()*1000)
        if kind == 'attempt_submitted':
            payload['text_length'] = len(payload['attempt_text'])
            if conversation_settings(events)['experience'] == 'chat':
                tracking = question_tracking.view(events)
                anchor = payload.get('question_event_id') or tracking['current_question_event_id']
                if not any(q['id'] == anchor for q in tracking['questions']):
                    raise HTTPException(422, 'Choose a question from this conversation.')
                payload.update(question_tracking.metadata(anchor))
            elif payload.get('question_event_id'):
                raise HTTPException(422, 'Question-turn references are only available in everyday conversations.')
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
    if kind == 'practice_invitation_responded' and payload['decision'] == 'try_myself':
        append(db, s, 'conversation_mode_changed', {'mode': 'try_myself', 'source': 'practice_invitation', 'decision_event_id': e.id})
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
        if conversation_settings(events)['experience'] == 'guided' and (pending_hints(events) or not currently_evaluated(events)):
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
        if str(body.regenerate_of or '') != str(old.payload.get('regenerate_of') or ''):
            raise HTTPException(409, 'Event ID reused for a different regeneration.')
        if body.help_action != old.payload.get('help_action'):
            raise HTTPException(409, 'Event ID reused with a different help action.')
        if body.answer_style != old.payload.get('answer_style', 'concise'):
            raise HTTPException(409, 'Event ID reused with a different answer length.')
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
            raise HTTPException(499 if result['payload'].get('cancelled') else 502, result['payload']['reason'])
        raise HTTPException(409, 'This request is still pending. Refresh the session to check its status.')
    if s.status != 'open':
        raise HTTPException(409, 'This session is closed.')
    if db.scalar(select(ConversationDeletion.id).where(ConversationDeletion.session_id==s.id, ConversationDeletion.status=='pending')):
        raise HTTPException(409, 'Conversation deletion is pending.')
    events = expire_interrupted(db, s, events)
    if in_flight(events):
        raise HTTPException(409, 'Another hint is already being requested.')
    settings = conversation_settings(events)
    is_chat = settings['experience'] == 'chat'
    if body.help_action and (not is_chat or body.tier != (2 if body.help_action == 'hint' else 3)):
        raise HTTPException(422, 'Choose a matching chat help action and level.')
    if not is_chat and not any(e['event_type'] in ('attempt_submitted', 'attempt_skipped') for e in events):
        raise HTTPException(409, 'Save an attempt or explicitly skip it first.')
    delivered = [e for e in events if e['event_type'] == 'ai_hint_delivered']
    expected = min(len(delivered)+1, 3)
    if not is_chat and body.followup_text and (body.tier != 3 or not any(e['payload']['tier'] == 3 for e in delivered)):
        raise HTTPException(409, 'Follow-up questions are available after the full explanation.')
    if not is_chat and (body.tier != expected or (len(delivered) >= 3 and not body.followup_text)):
        raise HTTPException(409, 'Request the next available hint level.')
    if is_chat and delivered and not body.followup_text and not body.help_action and not body.regenerate_of:
        raise HTTPException(409, 'Include a question or instruction for your next reply.')
    if not is_chat and pending_hints(events):
        raise HTTPException(409, 'Verify or explicitly skip the previous hint first.')
    context_events = events
    if body.regenerate_of:
        target = next((e for e in delivered if e['id'] == str(body.regenerate_of)), None)
        if not is_chat or not target or target != delivered[-1]:
            raise HTTPException(409, 'Regenerate the latest answer in this conversation.')
        source = next(e for e in events if e['id'] == target['payload']['request_event_id'])
        if any(e['event_type'] in ('attempt_submitted','ai_hint_requested') for e in events[events.index(target)+1:]):
            raise HTTPException(409, 'New work was saved after this answer. Ask a follow-up instead.')
        if (body.followup_text, body.help_action, body.tier) != (source['payload'].get('followup_text'), source['payload'].get('help_action'), source['payload']['tier_requested']):
            raise HTTPException(409, 'Regeneration must keep the original question and help level.')
        context_events = events[:events.index(source)]
    attempts = [e for e in context_events if e['event_type'] == 'attempt_submitted']
    config = provider.configuration(body.provider)
    provenance = {'provider': config['id'], 'model': config['model']}
    request_kind = 'followup' if body.followup_text else 'answer' if is_chat and body.tier == 3 else 'hint'
    conversation = []
    for event in events:
        if event['event_type'] == 'ai_hint_delivered':
            if event['payload'].get('followup_text'):
                conversation.append({'role': 'user', 'content': event['payload']['followup_text']})
            conversation.append({'role': 'assistant', 'content': event['payload']['hint_text']})
    problem = events[0]['payload']['problem_text']
    attempt = attempts[-1]['payload']['attempt_text'] if attempts else ''
    hints = [e['payload']['hint_text'] for e in delivered]
    followup = body.followup_text
    if is_chat:
        problem, attempt, conversation, followup = chat_context.context(context_events, body.followup_text, body.help_action)
        hints = []  # Relevant earlier answers are already in the chronological history.
    if body.help_action == 'check_thinking' and not attempt.strip():
        raise HTTPException(409, 'Save your thinking for the current question before asking for feedback.')
    question_meta = {}
    if is_chat:
        tracking = question_tracking.view(context_events)
        anchor = tracking['current_question_event_id']
        if body.regenerate_of:
            anchor = question_tracking.view(events)['event_questions'].get(source['id'])
            if not anchor:
                raise HTTPException(409, 'The source question is no longer available for regeneration.')
        elif question_tracking.explicit_question(body.model_dump()):
            anchor = str(body.event_id)
        question_meta = question_tracking.metadata(anchor)
    candidates = routing.order(body.provider)
    max_attempts = min(usage.limits()['max_attempts'], len(candidates))
    language = workspace.preferences(db,participant.id)['answer_language']
    purpose = body.help_action if body.help_action in ('exercise', 'check_thinking') else 'answer'
    budget = provider.attempt_budget(body.tier, problem, attempt, hints, conversation, followup, body.answer_style, candidates, purpose=purpose, language=language)
    usage.reserve(db, body.event_id, participant.id, budget, max_attempts)
    req = append(db, s, 'ai_hint_requested', {**provenance, 'selected_provider': body.provider,
                                            **question_meta,
                                            'answer_style': body.answer_style, 'help_action': body.help_action, 'focus_question': problem,
                                            'regenerate_of':str(body.regenerate_of) if body.regenerate_of else None, 'stream':body.stream, 'answer_language':language,
                                            **settings, 'request_kind': request_kind, 'followup_text': body.followup_text,
                                            'fallback_enabled': routing.enabled(), 'tier_requested': body.tier, 'preceded_by_attempt': bool(attempts),
                                            'time_since_session_start_ms': int((now()-timestamp(s.started_at)).total_seconds()*1000)}, body.event_id)
    db.add(ResponseDraft(request_id=req.id, session_id=s.id))
    commit(db, participant.id)  # Persist request before contacting provider, including on failure.
    request_id = req.id
    db.commit()  # Reading an expired ORM object may start a transaction; release it before network I/O.
    def record_attempt(report):
        session = locked(db, body.session_id, participant)
        report = dict(report)
        violation = report.pop('violation_response', None)
        usage.record_attempt(db, request_id, report)
        append(db, session, 'ai_provider_attempted', {**report, 'request_event_id': request_id})
        if violation is not None:
            append(db, session, 'hint_tier_violation', {'request_event_id': request_id, 'provider': report['provider'],
                   'model': report['model'], 'tier': body.tier, 'reason': 'Response exceeded hint level.', 'provider_response': violation})
        db.commit()
    last_preview = 0.0
    def cancelled():
        draft = db.get(ResponseDraft, request_id, populate_existing=True)
        result = bool(draft and draft.cancelled)
        db.commit()
        return result
    def preview(text):
        nonlocal last_preview
        if text and time.monotonic()-last_preview < 0.25:
            return
        draft = db.get(ResponseDraft, request_id, populate_existing=True)
        if draft.cancelled:
            db.commit()
            raise routing.Cancelled('Generation stopped. Usage already incurred still counts.')
        draft.text = text
        db.commit()
        last_preview = time.monotonic() if text else 0.0
    began = time.monotonic()
    try:
        generation = routing.generate(body.tier, problem, attempt, hints, body.provider,
                                 conversation, followup, record_attempt, body.answer_style, max_attempts,
                                 **({'on_delta':preview, 'cancelled':cancelled} if body.stream else {}),
                                 **({'language':language} if language!='auto' else {}),
                                 **({'purpose':purpose} if purpose!='answer' else {}))
    except SQLAlchemyError:
        raise
    except Exception as exc:
        s = locked(db, body.session_id, participant)
        if isinstance(exc, provider.TierViolation):
            append(db, s, 'hint_tier_violation', {**provenance, 'tier': body.tier, 'reason': str(exc), 'provider_response': exc.response})
        reason = str(exc) if isinstance(exc, (ValueError, provider.TierViolation)) else 'AI assistance could not connect. Your work is saved. Try again when ready.'
        draft = db.get(ResponseDraft, request_id, populate_existing=True)
        draft.text = ''
        stopped = isinstance(exc, routing.Cancelled) or draft.cancelled
        if stopped: reason = 'Generation stopped. Usage already incurred still counts.'
        append(db, s, 'ai_hint_failed', {**provenance, 'request_event_id': request_id, 'reason': reason, 'cancelled':stopped})
        usage.finish(db, request_id)
        commit(db, participant.id)
        raise HTTPException(499 if stopped else 502, reason) from exc
    s = locked(db, body.session_id, participant)
    if not any(e['id'] == request_id for e in in_flight(effective(timeline(db, s.id)))):
        raise HTTPException(409, 'This request has already finished. Retrieve its saved result.')
    draft = db.get(ResponseDraft, request_id, populate_existing=True)
    draft.text = ''
    if draft.cancelled:
        reason = 'Generation stopped. Usage already incurred still counts.'
        append(db, s, 'ai_hint_failed', {'request_event_id':request_id, 'reason':reason, 'cancelled':True})
        usage.finish(db, request_id)
        commit(db, participant.id)
        raise HTTPException(499, reason)
    result = append(db, s, 'ai_hint_delivered', {'provider': generation.provider or config['id'], 'model': generation.model or config['model'],
                                               **question_meta,
                                               'answer_style': body.answer_style, 'answer_language':language, 'usage': generation.usage,
                                               **settings, 'request_kind': request_kind, 'followup_text': body.followup_text,
                                               'help_action': body.help_action, 'focus_question': problem,
                                               'regenerate_of':str(body.regenerate_of) if body.regenerate_of else None,
                                               'reported_model': generation.reported_model, 'tier': body.tier, 'hint_text': generation.text, 'request_event_id': request_id,
                                               'model_latency_ms': int((time.monotonic()-began)*1000)})
    usage.finish(db, request_id)
    if body.help_action=='exercise':
        append(db,s,'conversation_mode_changed',{'mode':'try_myself','source':'related_exercise','answer_event_id':result.id})
    commit(db, participant.id)
    return serialize(result)


@app.get('/ai/usage')
def ai_usage(db=Depends(database), participant=Depends(user)):
    return usage.snapshot(db, participant.id, is_admin(participant.subject) or mode() == 'development')


@app.post('/ai/requests/{event_id}/cancel')
def cancel_answer(event_id: UUID, db=Depends(database), participant=Depends(user)):
    request = db.get(Event, str(event_id))
    if not request or request.user_id != participant.id or request.event_type != 'ai_hint_requested':
        raise HTTPException(404, 'The request is still starting or is not available.')
    session = locked(db, request.session_id, participant, False)
    if not any(e['id']==request.id for e in in_flight(effective(timeline(db,session.id)))):
        return {'status':'finished'}
    draft = db.get(ResponseDraft, request.id, populate_existing=True)
    if draft is None:
        draft = ResponseDraft(request_id=request.id, session_id=session.id)
        db.add(draft)
    draft.cancelled, draft.text = True, ''
    db.commit()
    return {'status':'stopping'}


@app.get('/ai/requests/{event_id}')
def request_status(event_id: UUID, db=Depends(database), participant=Depends(user)):
    request = db.get(Event, str(event_id))
    if not request or request.user_id != participant.id or request.event_type != 'ai_hint_requested':
        raise HTTPException(404, 'AI request not found.')
    session = locked(db, request.session_id, participant, False)
    events = expire_interrupted(db, session, effective(timeline(db, session.id)))
    result = next((e for e in events if e['event_type'] in ('ai_hint_delivered', 'ai_hint_failed') and e['payload'].get('request_event_id') == str(event_id)), None)
    commit(db, participant.id)
    draft = db.get(ResponseDraft, str(event_id))
    return {'status': 'pending' if result is None else 'delivered' if result['event_type'] == 'ai_hint_delivered' else 'cancelled' if result['payload'].get('cancelled') else 'failed', 'result': result,
            'preview':draft.text if draft and result is None and not draft.cancelled else '', 'stopping':bool(draft and draft.cancelled and result is None)}


@app.get('/analytics/me')
def personal(db=Depends(database), participant=Depends(user)):
    db.scalar(select(User).where(User.id == participant.id).with_for_update())
    row = db.get(Rollup, participant.id)
    if row is None or now()-timestamp(row.refreshed_at) > timedelta(minutes=5):
        row = refresh(db, participant.id)
    db.commit()
    return {**row.data, 'refreshed_at': timestamp(row.refreshed_at).isoformat()}


def analysis_result(events, request_id):
    return next((e for e in events if e['event_type'] in ('ai_analysis_delivered','ai_analysis_failed')
                 and e['payload'].get('request_event_id')==str(request_id)),None)


def expire_analyses(db,session,events):
    for e in events:
        if e['event_type']=='ai_analysis_requested' and not analysis_result(events,e['id']) and (now()-timestamp(e['created_at'])).total_seconds()>=90:
            append(db,session,'ai_analysis_failed',{'request_event_id':e['id'],'reason':'Review interrupted. You can request a new review when ready.'})
    return effective(timeline(db,session.id))


@app.get('/ai/analyses/{event_id}')
def analysis_status(event_id: UUID, db=Depends(database), participant=Depends(user)):
    request=db.get(Event,str(event_id))
    if not request or request.user_id!=participant.id or request.event_type!='ai_analysis_requested':
        raise HTTPException(404,'AI review not found.')
    session=locked(db,request.session_id,participant,False)
    events=expire_analyses(db,session,effective(timeline(db,session.id)))
    result=analysis_result(events,event_id)
    db.commit()
    return {'status':'pending' if result is None else 'delivered' if result['event_type']=='ai_analysis_delivered' else 'failed','result':result}


@app.post('/sessions/{sid}/analysis')
def review(sid: UUID, body: AnalysisRequest, db=Depends(database), participant=Depends(user)):
    if sid!=body.session_id:
        raise HTTPException(400,'The review must reference this conversation.')
    session=locked(db,sid,participant,False)
    if db.scalar(select(ConversationDeletion.id).where(ConversationDeletion.session_id==session.id,ConversationDeletion.status=='pending')):
        raise HTTPException(409, 'Conversation deletion is pending.')
    events=expire_analyses(db,session,effective(timeline(db,session.id)))
    if conversation_settings(events)['experience']!='chat':
        raise HTTPException(409,'AI reviews are available in everyday chats; guided study records keep their original protocol.')
    old=duplicate(db,body.event_id,participant,session.id,'ai_analysis_requested')
    if old:
        result=analysis_result(events,old.id)
        db.commit()
        if result and result['event_type']=='ai_analysis_delivered':return result
        if result:raise HTTPException(502,result['payload']['reason'])
        raise HTTPException(409,'This review is still pending.')
    context,fingerprint,truncated=activity.analysis_context(events)
    cached=next((e for e in reversed(events) if e['event_type']=='ai_analysis_delivered' and e['payload'].get('source_fingerprint')==fingerprint),None)
    if cached:
        db.commit()
        return cached
    if any(e['event_type']=='ai_analysis_requested' and not analysis_result(events,e['id']) for e in events):
        db.commit()
        raise HTTPException(409,'Another review is pending. Refresh to see its result.')
    if not activity.overview(events)['can_review']:
        raise HTTPException(409,'Save some thinking or get an answer before reviewing this conversation.')
    candidates=routing.order()
    max_attempts=min(usage.limits()['max_attempts'],len(candidates))
    language=workspace.preferences(db,participant.id)['answer_language']
    budget=provider.attempt_budget(3,context,'',[],None,None,'concise',candidates,'analysis',language=language)
    usage.reserve(db,body.event_id,participant.id,budget,max_attempts)
    request=append(db,session,'ai_analysis_requested',{'source_fingerprint':fingerprint,'excerpts_truncated':truncated,'answer_language':language},body.event_id)
    request_id=request.id
    db.commit()
    def record_attempt(report):
        current=locked(db,sid,participant,False)
        report={k:v for k,v in report.items() if k!='violation_response'}
        usage.record_attempt(db,request_id,report)
        append(db,current,'ai_analysis_provider_attempted',{**report,'request_event_id':request_id})
        db.commit()
    try:
        generation=routing.generate(3,context,'',[],None,None,None,record_attempt,'concise',max_attempts,'analysis',**({'language':language} if language!='auto' else {}))
    except SQLAlchemyError:
        raise
    except Exception as exc:
        session=locked(db,sid,participant,False)
        reason=str(exc) if isinstance(exc,ValueError) else 'The review could not finish. Your conversation is saved.'
        append(db,session,'ai_analysis_failed',{'request_event_id':request_id,'reason':reason})
        usage.finish(db,request_id)
        db.commit()
        raise HTTPException(502,reason) from exc
    session=locked(db,sid,participant,False)
    if analysis_result(effective(timeline(db,session.id)),request_id):
        raise HTTPException(409,'This review has already finished. Retrieve its saved result.')
    result=append(db,session,'ai_analysis_delivered',{'request_event_id':request_id,'source_fingerprint':fingerprint,
        'excerpts_truncated':truncated,'text':generation.text,'provider':generation.provider,'model':generation.model,
        'reported_model':generation.reported_model,'usage':generation.usage})
    usage.finish(db,request_id)
    db.commit()
    return serialize(result)


@app.get('/analytics/research')
def research(start: datetime | None = None, end: datetime | None = None, format: str = 'json', experience: str = 'guided',
             db=Depends(database), participant=Depends(user)):
    if not is_admin(participant.subject):
        raise HTTPException(403, 'Research administrator access required.')
    if format not in ('json', 'csv'):
        raise HTTPException(400, 'Format must be json or csv.')
    if experience not in ('guided', 'chat'):
        raise HTTPException(400, 'Choose either guided or chat experience for research analysis.')
    if start and end and timestamp(start) > timestamp(end):
        raise HTTPException(400, 'Start must precede end.')
    events = [serialize(e) for e in db.scalars(privacy.consenting_events())]
    rows = reconstruct(events)  # Reconstruct complete timelines before applying date filters.
    rows = [r for r in rows if not r.get('excluded') and r.get('experience', 'guided') == experience and
            (not start or timestamp(r['started_at']) >= timestamp(start)) and
            (not end or timestamp(r['started_at']) <= timestamp(end))]
    frame = user_frame(rows)
    if format == 'csv':
        return Response(frame.to_csv(index=False), media_type='text/csv',
                        headers={'Content-Disposition': f'attachment; filename="thinkfirst-{experience}-participants.csv"'})
    output = analyze(frame)
    output['refreshed_at'] = now().isoformat()
    output['session_count'] = len(rows)
    output['experience'] = experience
    db.add(ResearchExport(data=output))
    db.commit()
    return output
