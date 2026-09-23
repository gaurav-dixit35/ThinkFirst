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


class ConversationMode(Strict):
    mode: Literal['ask_ai', 'try_myself']


class PracticeDecision(Strict):
    answer_event_id: UUID
    decision: Literal['try_myself', 'continue_ai']


class AnswerFeedback(Strict):
    answer_event_id: UUID
    rating: Literal['helpful', 'not_helpful', 'cleared']


class Preferences(Strict):
    practice_reminders: bool = Field(strict=True)


class AnswerPreference(Strict):
    answer_style: Literal['concise', 'detailed']


class PrivacyChoices(Strict):
    research_opt_in: bool = Field(strict=True)
    acknowledge_notice: bool = Field(default=False, strict=True)


class DeleteConversations(Strict):
    confirmation: Literal['DELETE MY CONVERSATIONS']


class ConversationTitle(Strict):
    title: str | None = Field(default=None, min_length=1, max_length=100)


class AnalysisRequest(Strict):
    event_id: UUID
    session_id: UUID


class SavedAnswer(Strict):
    answer_event_id: UUID
    saved: bool = Field(strict=True)


class LearningAttempt(Strict):
    answer_event_id: UUID
    attempt_text: str = Field(min_length=1, max_length=20000)


PAYLOADS = {'attempt_submitted': Attempt, 'attempt_skipped': Skip,
            'verification_submitted': Verification, 'verification_skipped': VerificationSkip,
            'evaluation_submitted': Evaluation, 'evaluation_skipped': Strict,
            'attempt_correctness_reported': Correctness, 'event_invalidated': Invalidation,
            'conversation_mode_changed': ConversationMode,
            'practice_invitation_responded': PracticeDecision, 'answer_feedback': AnswerFeedback,
            'answer_saved': SavedAnswer, 'learning_attempt_submitted': LearningAttempt}


class Emit(Strict):
    event_id: UUID
    session_id: UUID
    event_type: str
    payload: dict


class Start(Strict):
    event_id: UUID
    problem_domain: Literal['coding', 'math', 'writing', 'general_reasoning']
    problem_text: str = Field(min_length=1, max_length=20000)
    experience: Literal['chat', 'guided'] = 'guided'
    initial_mode: Literal['ask_ai', 'try_myself'] = 'ask_ai'


class Hint(Strict):
    event_id: UUID
    session_id: UUID
    tier: Literal[1, 2, 3]
    provider: Literal['auto', 'gemini', 'groq', 'openrouter', 'mistral', 'cloudflare', 'anthropic'] | None = None
    followup_text: str | None = Field(default=None, min_length=1, max_length=5000)
    answer_style: Literal['concise', 'detailed'] = 'concise'
    help_action: Literal['hint', 'answer', 'exercise'] | None = None
    stream: bool = Field(default=False, strict=True)
    regenerate_of: UUID | None = None


class ArchiveConversation(Strict):
    archived: bool = Field(strict=True)


class DeleteConversation(Strict):
    confirmation: Literal['DELETE THIS CONVERSATION']


class EditQuestion(Strict):
    event_id: UUID
    source_event_id: UUID
    question: str = Field(min_length=1, max_length=20000)


class Close(Strict):
    event_id: UUID
    final_status: Literal['solved_independently', 'solved_with_ai', 'solved_without_ai_response', 'abandoned']


class LanguagePreference(Strict):
    answer_language: Literal['auto', 'english', 'hindi', 'hinglish']


class LearningGoal(Strict):
    goal: str = Field(max_length=160)
    weekly_target: int = Field(ge=0, le=50, strict=True)


class ReportProblem(Strict):
    id: UUID
    category: Literal['problem', 'suggestion', 'accessibility', 'ai_answer']
    message: str = Field(min_length=10, max_length=2000)
    reference: UUID | None = None


class ReportStatus(Strict):
    status: Literal['open', 'resolved']
