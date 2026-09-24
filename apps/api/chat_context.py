"""Resolve button help against the latest question without extra model calls."""
LEGACY_ACTIONS = {
    'Give me one small hint for my next step, using my latest saved attempt.': 'hint',
    'Explain the answer to the original question, taking my latest attempt into account.': 'answer',
}
ACTION_TEXT = {
    'check_thinking': 'Check my latest saved attempt for the current question. Give brief feedback and one useful next step without a worked solution.',
    'exercise': 'Create one new, related practice question for me to try. Do not include its answer or worked solution.',
    'hint': 'Give one useful hint for the current question, considering my saved attempt. If my attempt is already correct, help me check why rather than inventing a mistake.',
    'answer': 'Explain the answer to the current question, considering my saved attempt.',
}


def focus(events):
    question, boundary = '', -1
    for index, event in enumerate(events):
        p = event['payload']
        if event['event_type'] == 'session_started':
            question, boundary = p['problem_text'], index
        elif event['event_type'] == 'ai_hint_delivered' and p.get('help_action') == 'exercise':
            question, boundary = p['hint_text'], index
        elif event['event_type'] == 'ai_hint_requested' and p.get('followup_text') and not p.get('help_action') and not p.get('regenerate_of') and p['followup_text'] not in LEGACY_ACTIONS:
            question, boundary = p['followup_text'], index
    return question, boundary


def context(events, followup=None, action=None):
    from .question_tracking import view
    question, boundary = focus(events)
    action = action or LEGACY_ACTIONS.get(followup)
    # Explicit new messages establish a new focus. Previous attempts remain in
    # history with their question rather than being represented as new work.
    tracking = view(events)
    attempt_events = [e for e in events if e['event_type'] == 'attempt_submitted'
                      and tracking['event_questions'].get(e['id']) == tracking['current_question_event_id']]
    attempt = attempt_events[-1]['payload']['attempt_text'] if attempt_events else ''
    if followup and not action:
        question, attempt = followup, ''
    conversation = []
    for event in events:
        p = event['payload']
        if event['event_type'] == 'session_started':
            conversation.extend(p.get('branch_context', []))
            conversation.append({'role': 'user', 'content': p['problem_text']})
        elif event['event_type'] == 'ai_hint_requested' and p.get('followup_text'):
            old_action = p.get('help_action') or LEGACY_ACTIONS.get(p['followup_text'])
            conversation.append({'role': 'user', 'content': ACTION_TEXT[old_action] if old_action else p['followup_text']})
        elif event['event_type'] == 'attempt_submitted':
            label = 'My saved attempt: ' if tracking['event_questions'].get(event['id']) == tracking['current_question_event_id'] else 'My saved attempt for an earlier question (background only): '
            conversation.append({'role': 'user', 'content': label + p['attempt_text']})
        elif event['event_type'] == 'ai_hint_delivered':
            conversation.append({'role': 'assistant', 'content': p['hint_text']})
    return question, attempt, conversation, ACTION_TEXT[action] if action else followup
