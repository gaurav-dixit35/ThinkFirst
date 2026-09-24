"""Recorded question turns, not inferred topics or assessments of ability."""
from .chat_context import LEGACY_ACTIONS

VERSION = 'question-turn-v1'


def explicit_question(payload):
    return bool(payload.get('followup_text') and not payload.get('help_action')
                and not payload.get('regenerate_of') and payload['followup_text'] not in LEGACY_ACTIONS)


def view(events):
    questions, references, reports = {}, {}, {}
    current = None

    def add(event, text):
        questions[event['id']] = {'id': event['id'], 'text': text, 'attempts': 0,
                                 'attempt_before_first_request': None,
                                 'requests': {'answer': 0, 'hint': 0, 'check_thinking': 0, 'exercise': 0},
                                 'delivered': 0, 'verification': {'checked': 0, 'found_issue': 0, 'not_checked': 0}}
        return event['id']

    for event in events:
        kind, p, eid = event['event_type'], event['payload'], event['id']
        if kind == 'session_started':
            current = add(event, p['problem_text'])
        elif kind == 'ai_hint_requested' and explicit_question(p):
            current = add(event, p['followup_text'])
        anchor = p.get('question_event_id', current)
        if anchor not in questions:
            anchor = None  # Do not silently reassign work after an anchor is invalidated.
        if kind == 'ai_hint_requested' and p.get('regenerate_of'):
            anchor = references.get(p['regenerate_of'], anchor)
        if kind in ('ai_hint_delivered', 'ai_hint_failed'):
            anchor = references.get(p.get('request_event_id'), anchor)
        if kind == 'answer_verification_reported':
            anchor = references.get(p['answer_event_id'])
            reports[p['answer_event_id']] = p
        if kind in ('session_started', 'attempt_submitted', 'ai_hint_requested', 'ai_hint_delivered',
                    'ai_hint_failed', 'answer_verification_reported') and anchor:
            references[eid] = anchor
        if anchor:
            if kind == 'attempt_submitted':
                questions[anchor]['attempts'] += 1
            elif kind == 'ai_hint_requested':
                if questions[anchor]['attempt_before_first_request'] is None:
                    questions[anchor]['attempt_before_first_request'] = questions[anchor]['attempts'] > 0
                action = p.get('help_action') or LEGACY_ACTIONS.get(p.get('followup_text'))
                action = action or ('hint' if p.get('tier_requested', 3) < 3 else 'answer')
                questions[anchor]['requests'][action] += 1
            elif kind == 'ai_hint_delivered':
                questions[anchor]['delivered'] += 1
        if kind == 'ai_hint_delivered' and p.get('help_action') == 'exercise':
            current = add(event, p['hint_text'])
    for answer_id, report in reports.items():
        anchor = references.get(answer_id)
        if anchor:
            questions[anchor]['verification'][report['status']] += 1
    return {'version': VERSION, 'association': 'reconstructed_from_recorded_turns',
            'current_question_event_id': current, 'questions': list(questions.values()), 'event_questions': references}


def metadata(anchor):
    return {'question_event_id': anchor, 'question_tracking_version': VERSION}
