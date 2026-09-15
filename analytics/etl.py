"""Reconstruct timelines without mutating source events. All times are UTC."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def timestamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def effective(events):
    invalid = {e['payload']['target_event_id'] for e in events if e['event_type'] == 'event_invalidated'}
    return sorted([e for e in events if e['id'] not in invalid and e['event_type'] != 'event_invalidated'],
                  key=lambda e: (timestamp(e['created_at']), e['id']))


def reconstruct(events):
    grouped = defaultdict(list)
    for e in effective(events):
        grouped[e['session_id']].append(e)
    rows = []
    for sid, timeline in grouped.items():
        by = lambda kind: [e for e in timeline if e['event_type'] == kind]
        starts = by('session_started')
        if len(starts) != 1:
            rows.append({'session_id': sid, 'excluded': True, 'quality_flags': ['missing_or_duplicate_start']})
            continue
        start = timestamp(starts[0]['created_at'])
        requests, attempts, deliveries = by('ai_hint_requested'), by('attempt_submitted'), by('ai_hint_delivered')
        first_ai = timestamp(requests[0]['created_at']) if requests else None
        pre = [a for a in attempts if first_ai is None or timestamp(a['created_at']) < first_ai]
        effort = max([(min(len(a['payload']['attempt_text']) / 500, 1) +
                       min(max((timestamp(a['created_at']) - start).total_seconds(), 0) / 300, 1)) / 2
                      for a in pre], default=0)
        correctness = {e['payload']['attempt_event_id']: e['payload']['adequate'] for e in by('attempt_correctness_reported')}
        assessed = [a for a in attempts if a['id'] in correctness]
        unnecessary = None if not assessed else any(correctness[a['id']] and any(timestamp(r['created_at']) > timestamp(a['created_at']) for r in requests) for a in assessed)
        close = by('session_closed')
        final = close[-1]['payload']['final_status'] if close else 'open'
        verified = {e['payload']['hint_event_id'] for e in by('verification_submitted')}
        verified &= {e['id'] for e in deliveries}
        flags = []
        if any(timestamp(e['created_at']) < start for e in timeline):
            flags.append('negative_duration')
        if close and close[-1]['payload']['total_duration_ms'] < 0:
            flags.append('negative_duration')
        if requests and not deliveries:
            flags.append('no_ai_response')
        if final == 'open':
            flags.append('incomplete_session')
        rows.append(dict(session_id=sid, user_id=starts[0]['user_id'], started_at=start.isoformat(),
                         problem_domain=starts[0]['payload']['problem_domain'], final_status=final,
                         is_ai_first=bool(requests and not pre), ai_requests=len(requests), ai_responses=len(deliveries),
                         first_ai_at=first_ai.isoformat() if first_ai else None,
                         time_to_ai_seconds=(first_ai-start).total_seconds() if first_ai else None,
                         attempt_effort_score=effort, verification_count=len(verified),
                         verification_rate=len(verified)/len(deliveries) if deliveries else None,
                         unnecessary_ai_use_flag=unnecessary,
                         no_ai_completion=final == 'solved_independently' and not requests,
                         evaluation_completed=bool(by('evaluation_submitted') and deliveries and timestamp(by('evaluation_submitted')[-1]['created_at']) > timestamp(deliveries[-1]['created_at']) and (not by('evaluation_skipped') or timestamp(by('evaluation_submitted')[-1]['created_at']) > timestamp(by('evaluation_skipped')[-1]['created_at']))),
                         attempt_skipped=bool(by('attempt_skipped')),
                         quality_flags=flags, excluded='negative_duration' in flags))
    all_requests = [e for e in effective(events) if e['event_type'] == 'ai_hint_requested']
    for row in rows:
        if row.get('excluded'):
            continue
        anchor = timestamp(row['first_ai_at'] or row['started_at'])
        row['prior_7d_ai_requests'] = sum(e['user_id'] == row['user_id'] and anchor-timedelta(days=7) <= timestamp(e['created_at']) < anchor for e in all_requests)
    return rows


def summarize(rows, events, at=None):
    at = at or datetime.now(timezone.utc)
    valid = [r for r in rows if not r.get('excluded')]
    closed = [r for r in valid if r['final_status'] != 'open']
    ai = [r for r in valid if r['ai_requests']]
    delivered = sum(r['ai_responses'] for r in valid)
    reqs = [e for e in effective(events) if e['event_type'] == 'ai_hint_requested']
    weekly = defaultdict(list)
    for r in valid:
        day = timestamp(r['started_at']).date()
        weekly[(day-timedelta(days=day.weekday())).isoformat()].append(r)
    trend = []
    for week, group in sorted(weekly.items()):
        used = [r for r in group if r['ai_requests']]
        count = sum(r['ai_responses'] for r in group)
        times = [r['time_to_ai_seconds'] for r in used]
        trend.append(dict(week=week, ai_first_ratio=sum(r['is_ai_first'] for r in used)/len(used) if used else None,
                          verification_rate=sum(r['verification_count'] for r in group)/count if count else None,
                          time_to_ai_seconds=sum(times)/len(times) if times else None))
    return dict(sessions_total=len(valid), sessions_closed=len(closed),
                ai_requests_7d=sum(at-timedelta(days=7) <= timestamp(e['created_at']) <= at for e in reqs),
                ai_requests_30d=sum(at-timedelta(days=30) <= timestamp(e['created_at']) <= at for e in reqs),
                ai_first_ratio=sum(r['is_ai_first'] for r in ai)/len(ai) if ai else None,
                verification_rate=sum(r['verification_count'] for r in valid)/delivered if delivered else None,
                no_ai_completion_rate=sum(r['no_ai_completion'] for r in closed)/len(closed) if closed else None,
                evaluation_completion_rate=sum(r['evaluation_completed'] for r in ai)/len(ai) if ai else None,
                skip_rate=sum(r['attempt_skipped'] for r in valid)/len(valid) if valid else None,
                trend=trend, quality_flagged_sessions=sum(bool(r.get('quality_flags')) for r in rows))


def user_frame(rows):
    import pandas as pd
    grouped = defaultdict(list)
    for row in rows:
        if not row.get('excluded') and row['final_status'] != 'open':
            grouped[row['user_id']].append(row)
    result = []
    for user, group in grouped.items():
        ai = [r for r in group if r['ai_requests']]
        if not ai:
            continue  # first-action preference cannot be inferred without an AI request
        adequacy = [r['unnecessary_ai_use_flag'] for r in group if r['unnecessary_ai_use_flag'] is not None]
        responses = sum(r['ai_responses'] for r in group)
        result.append(dict(user_id=user, is_ai_first=int(sum(r['is_ai_first'] for r in ai)/len(ai) >= .5),
                           ai_usage_frequency=sum(r['prior_7d_ai_requests'] for r in ai)/len(ai),
                           attempt_effort_score=sum(r['attempt_effort_score'] for r in group)/len(group),
                           verification_rate=sum(r['verification_count'] for r in group)/responses if responses else None,
                           unnecessary_ai_use_flag=sum(adequacy)/len(adequacy) if adequacy else None,
                           no_ai_completion_rate=sum(r['no_ai_completion'] for r in group)/len(group),
                           evaluation_completion_rate=sum(r['evaluation_completed'] for r in ai)/len(ai)))
    return pd.DataFrame(result, columns=['user_id', 'is_ai_first', 'ai_usage_frequency',
                                        'attempt_effort_score', 'verification_rate', 'unnecessary_ai_use_flag',
                                        'no_ai_completion_rate', 'evaluation_completion_rate'])
