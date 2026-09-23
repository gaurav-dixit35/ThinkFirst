"""Owner preferences and factual weekly goals; no AI work is performed here."""
from datetime import timedelta
from sqlalchemy import select
from analytics.etl import effective, timestamp
from .db import LearningPreferences, Event, now


def preferences(db, user_id):
    row = db.get(LearningPreferences, user_id)
    return {'answer_language':row.answer_language if row else 'auto',
            'goal':row.goal if row else '', 'weekly_target':row.weekly_target if row else 0}


def goal_progress(db, user_id):
    at = now()
    start = (at - timedelta(days=at.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    # Include corrections from any date so a later invalidation also removes the
    # corresponding retry from this week's factual counts.
    rows = db.scalars(select(Event).where(Event.user_id==user_id, Event.event_type.in_(['learning_attempt_submitted','event_invalidated'])))
    events = effective([{'id':e.id, 'event_type':e.event_type, 'payload':e.payload, 'created_at':e.created_at} for e in rows])
    attempts = [e for e in events if timestamp(e['created_at'])>=start and timestamp(e['created_at'])<start+timedelta(days=7)]
    return {**preferences(db,user_id), 'questions_retried':len({e['payload']['answer_event_id'] for e in attempts}),
            'attempts':len(attempts), 'week_start':start.isoformat(), 'resets_at':(start+timedelta(days=7)).isoformat()}
