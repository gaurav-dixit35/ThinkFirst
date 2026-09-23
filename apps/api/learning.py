"""Saved answers and deliberate retries. No model calls and no inferred grades."""
from collections import defaultdict
from sqlalchemy import select
from analytics.etl import effective, timestamp
from .db import Event, ConversationDeletion
from .chat_context import focus


def saved_state(events):
    result = {}
    for event in events:
        if event['event_type'] == 'answer_saved':
            result[event['payload']['answer_event_id']] = event['payload']['saved']
    return result


def library(db, user_id):
    # Load only conversations with bookmark activity; source text remains in the
    # original events so ordinary conversation erasure also removes saved work.
    sessions = select(Event.session_id).where(Event.user_id == user_id, Event.event_type == 'answer_saved').distinct()
    groups = defaultdict(list)
    for event in db.scalars(select(Event).where(Event.user_id == user_id, Event.session_id.in_(sessions)).order_by(Event.created_at, Event.id)):
        groups[event.session_id].append({'id':event.id, 'event_type':event.event_type,
                                        'payload':event.payload, 'created_at':timestamp(event.created_at).isoformat()})
    deleting = set(db.scalars(select(ConversationDeletion.session_id).where(ConversationDeletion.user_id == user_id, ConversationDeletion.status == 'pending')))
    result = []
    for sid, raw in groups.items():
        events = effective(raw)
        states = saved_state(events)
        for index, answer in enumerate(events):
            if answer['event_type'] != 'ai_hint_delivered' or not states.get(answer['id']):
                continue
            # Regeneration must refer to its original question even if a newer
            # question appeared before the replacement answer was delivered.
            request_id = answer['payload'].get('request_event_id')
            request_index = next((i for i,e in enumerate(events) if e['id'] == request_id), index)
            request = events[request_index]
            original = request['payload'].get('regenerate_of')
            if original:
                source = next((e for e in events if e['id'] == original), None)
                if source:
                    request_index = next((i for i,e in enumerate(events) if e['id'] == source['payload'].get('request_event_id')), request_index)
            question, _ = focus(events[:request_index+1])
            attempts = [{'id':e['id'], 'text':e['payload']['attempt_text'], 'created_at':e['created_at']}
                        for e in events if e['event_type'] == 'learning_attempt_submitted' and e['payload']['answer_event_id'] == answer['id']]
            bookmark = next(e for e in reversed(events) if e['event_type']=='answer_saved' and e['payload']['answer_event_id']==answer['id'])
            result.append({'answer_id':answer['id'], 'session_id':sid, 'question':question,
                           'answer':answer['payload']['hint_text'], 'saved_at':bookmark['created_at'],
                           'attempts':attempts, 'deletion_pending':sid in deleting})
    return sorted(result, key=lambda item:(item['saved_at'],item['answer_id']), reverse=True)
