"""Bounded failover and process-local provider cooldowns; attempts remain auditable."""
import asyncio
import hashlib
import os
import threading
import time
from typing import Callable
from . import provider
from .usage import limits

DEFAULT_ORDER = 'groq,gemini,openrouter,mistral,cloudflare'
_cooldowns: dict[str, float] = {}
_lock = threading.Lock()


def enabled():
    return os.getenv('AI_FALLBACK_ENABLED', 'true').lower() not in ('false', '0', 'no')


def seconds(name, default, low, high):
    try:
        return max(low, min(float(os.getenv(name, default)), high))
    except ValueError:
        return default


def order(preferred=None):
    names = [x.strip().lower() for x in os.getenv('AI_FALLBACK_ORDER', DEFAULT_ORDER).split(',') if x.strip()]
    unknown = set(names) - set(provider.PROVIDERS)
    if unknown:
        raise ValueError('AI_FALLBACK_ORDER contains an unknown provider.')
    first = provider.configuration(preferred)['id']
    return list(dict.fromkeys([first] + names)) if enabled() else [first]


def fingerprint(config):
    material = '|'.join([config['id'], config['model'], provider.api_key(config['id']), os.getenv('CLOUDFLARE_ACCOUNT_ID', '')])
    return hashlib.sha256(material.encode()).hexdigest()


def reset_cooldowns():
    with _lock:
        _cooldowns.clear()


class Cancelled(ValueError):
    pass


class Exhausted(ValueError):
    pass


async def _generate(tier, problem, attempt, hints, preferred, conversation, followup_text, on_attempt, answer_style, max_attempts, purpose, on_delta=None, cancelled=None):
    started = time.monotonic()
    budget = seconds('AI_TOTAL_TIMEOUT_SECONDS', 50, 5, 55)
    per_attempt = seconds('AI_PROVIDER_TIMEOUT_SECONDS', 9, 1, 30)
    candidates = order(preferred)
    attempted = 0
    configured = 0
    for index, name in enumerate(candidates, 1):
        if cancelled and cancelled():
            raise Cancelled("Generation stopped. Usage already incurred still counts.")
        config = provider.configuration(name)
        report = dict(attempt_index=index, provider=name, model=config['model'], outcome='skipped', error_code=None,
                      latency_ms=0, retry_after_seconds=None)
        if not config['configured']:
            on_attempt({**report, 'error_code': 'not_configured'})
            continue
        configured += 1
        key = fingerprint(config)
        with _lock:
            remaining_cooldown = max(0, _cooldowns.get(key, 0) - time.monotonic())
        if remaining_cooldown:
            on_attempt({**report, 'error_code': 'cooldown', 'retry_after_seconds': round(remaining_cooldown, 2)})
            continue
        remaining = budget - (time.monotonic() - started)
        if remaining <= 0:
            on_attempt({**report, 'error_code': 'deadline'})
            break
        if attempted >= max_attempts:
            on_attempt({**report, 'error_code': 'attempt_limit'})
            break
        began = time.monotonic()
        attempted += 1
        violation = None
        usage = None
        try:
            async with asyncio.timeout(min(per_attempt, remaining)):
                if on_delta:
                    on_delta('')  # Replace a failed provider's preview; never concatenate fallbacks.
                args = (tier, problem, attempt, hints, name, conversation, followup_text, answer_style, purpose)
                task = asyncio.create_task(provider.generate_async(*args, **({'on_delta':on_delta} if on_delta else {})))
                try:
                    while not task.done():
                        if cancelled and cancelled():
                            raise Cancelled('Generation stopped. Usage already incurred still counts.')
                        await asyncio.wait({task}, timeout=0.2)
                    result = await task
                finally:
                    if not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
            with _lock:
                _cooldowns.pop(key, None)
            on_attempt({**report, 'outcome': 'success', 'latency_ms': int((time.monotonic()-began)*1000), 'usage': result.usage})
            result.provider = name
            result.model = config['model']
            return result
        except Cancelled:
            on_attempt({**report, 'outcome':'failed', 'error_code':'cancelled', 'usage':None,
                        'latency_ms':int((time.monotonic()-began)*1000)})
            raise
        except provider.TierViolation as exc:
            usage = getattr(exc, 'usage', None)
            code, retry_after = 'tier_violation', 0
            violation = exc.response
        except provider.ProviderError as exc:
            usage = getattr(exc, 'usage', None)
            code, retry_after = exc.code, exc.retry_after
            if not exc.recoverable:
                on_attempt({**report, 'outcome': 'failed', 'error_code': code, 'latency_ms': int((time.monotonic()-began)*1000), 'usage': usage})
                raise Exhausted('AI could not respond to this request. Your work is saved; try rephrasing your question.') from exc
        except (TimeoutError, asyncio.TimeoutError):
            code, retry_after = 'timeout', 20
        except ValueError as exc:
            usage = getattr(exc, 'usage', None)
            code, retry_after = 'invalid_response', 15
        except Exception:
            on_attempt({**report, 'outcome': 'failed', 'error_code': 'unexpected_error', 'usage': None,
                        'latency_ms': int((time.monotonic()-began)*1000)})
            raise
        cooldown = max(retry_after or 0, 300 if code in ('authentication', 'credits', 'model_unavailable') else 20 if code in ('rate_limit', 'timeout', 'unavailable') else 0)
        if cooldown:
            with _lock:
                if len(_cooldowns) > 512:
                    _cooldowns.clear()
                _cooldowns[key] = time.monotonic() + min(cooldown, 300)
        on_attempt({**report, 'outcome': 'failed', 'error_code': code,
                    'usage': usage,
                    'latency_ms': int((time.monotonic()-began)*1000), 'retry_after_seconds': cooldown or None,
                    **({'violation_response': violation} if violation is not None else {})})
    if not configured:
        raise Exhausted('AI assistance is not configured yet. Add a provider key to .env and restart the API. Your work is saved and you can still finish independently.')
    if not attempted:
        raise Exhausted('AI services are temporarily busy. Your question is saved; please retry shortly.')
    raise Exhausted('AI assistance is temporarily unavailable. Your question and conversation are saved. Please retry shortly.')


def generate(tier, problem, attempt, hints, preferred=None, conversation=None, followup_text=None, on_attempt: Callable | None = None,
             answer_style='concise', max_attempts=None, purpose='answer', on_delta=None, cancelled=None):
    return asyncio.run(_generate(tier, problem, attempt, hints, preferred, conversation, followup_text,
                                on_attempt or (lambda report: None), answer_style,
                                max_attempts or limits()['max_attempts'], purpose, on_delta, cancelled))
