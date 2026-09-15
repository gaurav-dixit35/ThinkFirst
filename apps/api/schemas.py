from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Attempt(Strict):
    attempt_text: str = Field(min_length=1, max_length=20000)
    is_partial: bool = True


class Skip(Strict):
    skip_reason: str | None = Field(default=None, max_length=1000)


class Verification(Strict):
    hint_event_id: UUID
    matches_own_attempt: bool | None
    justification: str = Field(min_length=1, max_length=5000)


class VerificationSkip(Strict):
    hint_event_id: UUID


class Evaluation(Strict):
    makes_sense: bool
    reasoning: str = Field(min_length=1, max_length=5000)


class Correctness(Strict):
    attempt_event_id: UUID
    adequate: bool


class Invalidation(Strict):
    target_event_id: UUID
    reason: str = Field(min_length=1, max_length=1000)


PAYLOADS = {'attempt_submitted': Attempt, 'attempt_skipped': Skip,
            'verification_submitted': Verification, 'verification_skipped': VerificationSkip,
            'evaluation_submitted': Evaluation, 'evaluation_skipped': Strict,
            'attempt_correctness_reported': Correctness, 'event_invalidated': Invalidation}


class Emit(Strict):
    event_id: UUID
    session_id: UUID
    event_type: str
    payload: dict


class Start(Strict):
    event_id: UUID
    problem_domain: Literal['coding', 'math', 'writing', 'general_reasoning']
    problem_text: str = Field(min_length=1, max_length=20000)


class Hint(Strict):
    event_id: UUID
    session_id: UUID
    tier: Literal[1, 2, 3]
    provider: Literal['auto', 'gemini', 'groq', 'openrouter', 'mistral', 'cloudflare', 'anthropic'] | None = None
    followup_text: str | None = Field(default=None, min_length=1, max_length=5000)


class Close(Strict):
    event_id: UUID
    final_status: Literal['solved_independently', 'solved_with_ai', 'solved_without_ai_response', 'abandoned']
