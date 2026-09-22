"""Optional practice eligibility from saved behavior; never invokes a model."""
from datetime import timedelta
from analytics.etl import timestamp
from .db import UserPreferences, now

TASKS = {
    'math': 'Work through one step yourself. How could you check it by substitution or another method?',
    'coding': 'Trace a small example or write one yourself. What output do you expect, and why?',
    'writing': 'Write one sentence in your own voice. What do you want it to communicate?',
    'general_reasoning': 'Explain your answer in your own words, with one reason or example that supports it.',
}


def preferences(db, user_id):
    row = db.get(UserPreferences, user_id)
    return {'practice_reminders': row.practice_reminders if row else True}


def state(events, enabled=True, closed=False, at=None):
    at = at or now()
    start = next(e for e in events if e['event_type'] == 'session_started')
    mode = start['payload'].get('initial_mode', 'ask_ai')
    streak, decisions, anchor, last_decision, active = 0, 0, None, None, None
    questions = {e['id']: e['payload'].get('focus_question') or e['payload'].get('followup_text') for e in events if e['event_type'] == 'ai_hint_requested'}
    for event in events:
        kind, payload = event['event_type'], event['payload']
        if kind == 'conversation_mode_changed':
            mode = payload['mode']
            if mode == 'try_myself':
                streak, anchor = 0, None
        elif kind == 'attempt_submitted':
            streak, anchor, active = 0, None, None
        elif kind == 'practice_invitation_responded':
            decisions += 1
            last_decision = timestamp(event['created_at'])
            streak, anchor = 0, None
            active = payload['answer_event_id'] if payload['decision'] == 'try_myself' else None
        elif kind == 'ai_hint_delivered' and payload.get('mode', mode) == 'ask_ai' and mode == 'ask_ai':
            streak += 1
            if streak == 3:
                anchor = event['id']
    eligible = (enabled and not closed and start['payload'].get('experience', 'guided') == 'chat'
                and mode == 'ask_ai' and anchor is not None and decisions < 2
                and (last_decision is None or at >= last_decision + timedelta(minutes=10)))
    target_id = active or anchor
    answer = next((e for e in events if e['id'] == target_id), None)
    question = (answer['payload'].get('focus_question') or questions.get(answer['payload'].get('request_event_id')) or answer['payload'].get('followup_text')) if answer else None
    return dict(eligible=bool(eligible), answer_event_id=anchor if eligible else None,
                reminders_enabled=enabled, active=bool(active and mode == 'try_myself' and not closed),
                question=question or start['payload']['problem_text'],
                task=TASKS.get(start['payload']['problem_domain'], TASKS['general_reasoning']))
