"""Atomic request admission and conservative, durable fallback accounting.

Reserve the entire fallback envelope before network I/O. Unknown usage (including
timeouts) keeps its full attempt reservation. Dollar figures are estimates using
an operator-supplied rate ceiling, never a claim about the provider's invoice.
"""
import os
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from fastapi import HTTPException
from sqlalchemy import select, func, update
from .db import AIBudgetLock, AIUsageRequest, now


def integer(name, default):
    try:
        value = int(os.getenv(name, str(default)))
        if value < 1:
            raise ValueError()
        return value
    except ValueError as exc:
        raise ValueError(f'{name} must be a positive integer.') from exc


def micro_usd(name):
    try:
        value = Decimal(os.getenv(name, '0'))
        if not value.is_finite() or value < 0:
            raise InvalidOperation()
        return int((value * 1_000_000).to_integral_value(rounding=ROUND_CEILING))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'{name} must be a non-negative dollar amount.') from exc


def limits():
    values = dict(daily_requests=integer('AI_USER_DAILY_REQUESTS', 30),
                  requests_per_minute=integer('AI_USER_REQUESTS_PER_MINUTE', 6),
                  user_concurrency=integer('AI_USER_CONCURRENCY', 2),
                  global_concurrency=integer('AI_GLOBAL_CONCURRENCY', 8),
                  daily_tokens=integer('AI_GLOBAL_DAILY_TOKENS', 1_000_000),
                  max_attempts=min(6, integer('AI_MAX_PROVIDER_ATTEMPTS', 3)),
                  budget_micro_usd=micro_usd('AI_GLOBAL_DAILY_BUDGET_USD'),
                  rate_micro_usd_per_million=micro_usd('AI_MAX_USD_PER_MILLION_TOKENS'))
    if values['budget_micro_usd'] and not values['rate_micro_usd_per_million']:
        raise ValueError('A dollar budget requires AI_MAX_USD_PER_MILLION_TOKENS. Set a ceiling covering every configured model and token type.')
    return values


def lock(db):
    # A real write serializes admission on SQLite as well as PostgreSQL workers.
    db.execute(update(AIBudgetLock).where(AIBudgetLock.id == 1).values(id=1))


def day_start():
    return now().replace(hour=0, minute=0, second=0, microsecond=0)


def cost(tokens, rate):
    return (tokens * rate + 999_999) // 1_000_000


def count(db, *conditions):
    return db.scalar(select(func.count()).select_from(AIUsageRequest).where(*conditions)) or 0


def totals(db):
    row = db.execute(select(func.coalesce(func.sum(AIUsageRequest.accounted_tokens), 0),
                            func.coalesce(func.sum(AIUsageRequest.accounted_micro_usd), 0))
                     .where(AIUsageRequest.created_at >= day_start())).one()
    return int(row[0]), int(row[1])


def reserve(db, request_id, user_id, attempt_budget, max_attempts):
    config = limits()
    lock(db)
    daily = count(db, AIUsageRequest.user_id == user_id, AIUsageRequest.created_at >= day_start())
    recent = count(db, AIUsageRequest.user_id == user_id, AIUsageRequest.created_at >= now()-timedelta(minutes=1))
    active = (AIUsageRequest.status == 'pending', AIUsageRequest.created_at >= now()-timedelta(seconds=90))
    message = None
    if daily >= config['daily_requests']:
        message = 'Your daily AI allowance is used up. It resets at midnight UTC. You can still save your own thinking.'
    elif recent >= config['requests_per_minute']:
        message = 'Please wait a minute before asking AI again. Your draft is saved.'
    elif count(db, *active, AIUsageRequest.user_id == user_id) >= config['user_concurrency']:
        message = 'Please let one of your pending AI replies finish first.'
    elif count(db, *active) >= config['global_concurrency']:
        message = 'AI is busy right now. Please retry shortly; your draft is saved.'
    used_tokens, used_cost = totals(db)
    reserved = attempt_budget * max_attempts
    estimate = cost(reserved, config['rate_micro_usd_per_million'])
    if not message and (used_tokens + reserved > config['daily_tokens'] or
                        config['budget_micro_usd'] and used_cost + estimate > config['budget_micro_usd']):
        message = 'The shared AI allowance cannot fit this request right now. Try a shorter conversation or return after midnight UTC. You can still save your own thinking.'
    if message:
        raise HTTPException(429, message, headers={'Retry-After': '60'})
    db.add(AIUsageRequest(id=str(request_id), user_id=user_id, attempt_budget=attempt_budget,
                         max_attempts=max_attempts, accounted_tokens=reserved, accounted_micro_usd=estimate,
                         rate_micro_usd_per_million=config['rate_micro_usd_per_million'], attempts=[]))
    db.flush()


def record_attempt(db, request_id, report):
    if report['outcome'] == 'skipped':
        return
    lock(db)
    row = db.get(AIUsageRequest, str(request_id), populate_existing=True)
    if not row or any(a['attempt_index'] == report['attempt_index'] for a in row.attempts):
        return
    # Persist just metadata, never prompts, keys, or rejected answer text.
    row.attempts = [*row.attempts, {k: v for k, v in report.items() if k != 'violation_response'}]
    # If the provider reports more than our envelope, expose the overage now.
    # Never hide it until completion or assume an estimate is an invoice cap.
    row.accounted_tokens += max(0, ((report.get('usage') or {}).get('total_tokens') or 0)-row.attempt_budget)
    row.accounted_micro_usd += max(0,
        max(cost((report.get('usage') or {}).get('total_tokens') or row.attempt_budget, row.rate_micro_usd_per_million),
            (report.get('usage') or {}).get('cost_micro_usd') or 0)-cost(row.attempt_budget, row.rate_micro_usd_per_million))
    db.flush()


def finish(db, request_id):
    lock(db)
    row = db.get(AIUsageRequest, str(request_id), populate_existing=True)
    if not row or row.status != 'pending':
        return
    tokens = dollars = 0
    for attempt in row.attempts:
        usage = attempt.get('usage') or {}
        measured = usage.get('total_tokens')
        billed = measured if isinstance(measured, int) else row.attempt_budget
        tokens += billed
        dollars += max(cost(billed, row.rate_micro_usd_per_million), usage.get('cost_micro_usd') or 0)
    row.accounted_tokens, row.accounted_micro_usd = tokens, dollars
    row.status = 'finished'
    db.flush()


def snapshot(db, user_id, operator=False):
    config = limits()
    used = count(db, AIUsageRequest.user_id == user_id, AIUsageRequest.created_at >= day_start())
    result = dict(daily_limit=config['daily_requests'], requests_used=used,
                  requests_remaining=max(0, config['daily_requests']-used),
                  resets_at=(day_start()+timedelta(days=1)).isoformat())
    if operator:
        tokens, dollars = totals(db)
        rows = db.scalars(select(AIUsageRequest).where(AIUsageRequest.created_at >= day_start())).all()
        attempts = [a for row in rows for a in row.attempts]
        result['workspace'] = dict(accounted_tokens=tokens, daily_token_limit=config['daily_tokens'],
            estimated_or_reserved_usd=dollars/1_000_000,
            daily_budget_usd=config['budget_micro_usd']/1_000_000 or None,
            dollar_budget_enabled=bool(config['budget_micro_usd']),
            rate_ceiling_usd_per_million=config['rate_micro_usd_per_million']/1_000_000 or None,
            provider_attempts=len(attempts), reported_tokens=sum((a.get('usage') or {}).get('total_tokens') or 0 for a in attempts),
            attempts_without_usage=sum(not a.get('usage') or a['usage'].get('total_tokens') is None for a in attempts),
            max_attempts=config['max_attempts'])
    return result
