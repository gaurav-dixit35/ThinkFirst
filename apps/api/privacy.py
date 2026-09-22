"""Account data choices. Research consent is never inferred from app use."""
from sqlalchemy import select
from .db import UserPrivacy, DeletionRequest, Session, Event, ConversationMetadata, ConversationState, ConversationDeletion, ResponseDraft, UserPreferences, AnswerPreferences, AIUsageRequest, now

NOTICE_VERSION = '2026-09-16'


def pending(db, user_id):
    return db.scalar(select(DeletionRequest).where(DeletionRequest.user_id == user_id, DeletionRequest.status == 'pending'))


def state(db, user_id):
    row = db.get(UserPrivacy, user_id)
    requests = list(db.scalars(select(DeletionRequest).where(DeletionRequest.user_id == user_id).order_by(DeletionRequest.created_at.desc())))
    return {'notice_version': NOTICE_VERSION, 'acknowledged': bool(row and row.notice_version == NOTICE_VERSION),
            'research_opt_in': bool(row and row.research_opt_in),
            'deletion_request': record(requests[0]) if requests else None,
            'last_erased_at': next((r.completed_at.isoformat() for r in requests if r.completed_at), None)}


def record(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def consenting_events():
    return select(Event).join(UserPrivacy, UserPrivacy.user_id == Event.user_id).where(UserPrivacy.research_opt_in.is_(True), ~Event.session_id.in_(select(ConversationDeletion.session_id).where(ConversationDeletion.status=='pending')))


def export_account(db, participant):
    sessions = list(db.scalars(select(Session).where(Session.user_id == participant.id)))
    ids = [s.id for s in sessions]
    preferences = db.get(UserPreferences, participant.id)
    choices = db.get(UserPrivacy, participant.id)
    answers = db.get(AnswerPreferences, participant.id)
    return {'schema_version': 1, 'exported_at': now(), 'account': record(participant),
            'privacy': state(db, participant.id), 'privacy_record': record(choices) if choices else None,
            'preferences': record(preferences) if preferences else {'practice_reminders': True},
            'answer_preferences': record(answers) if answers else {'answer_style': 'concise'},
            'sessions': [record(s) for s in sessions],
            'conversation_state': [record(r) for r in db.scalars(select(ConversationState).where(ConversationState.session_id.in_(ids)))],
            'conversation_deletions': [record(r) for r in db.scalars(select(ConversationDeletion).where(ConversationDeletion.user_id==participant.id))],
            'titles': [record(m) for m in db.scalars(select(ConversationMetadata).where(ConversationMetadata.session_id.in_(ids)))],
            'events': [record(e) for e in db.scalars(select(Event).where(Event.user_id == participant.id).order_by(Event.created_at, Event.id))],
            'usage': [record(r) for r in db.scalars(select(AIUsageRequest).where(AIUsageRequest.user_id == participant.id))],
            'deletion_requests': [record(r) for r in db.scalars(select(DeletionRequest).where(DeletionRequest.user_id == participant.id))]}
