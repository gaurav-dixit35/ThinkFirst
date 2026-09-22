## PART 4 — COMPLETE EVENT SCHEMA

This is the contract. Every event has: `event_id` (UUID), `user_id`, `session_id`, `event_type`, `payload` (JSONB), `created_at` (server timestamp, authoritative — never trust client timestamps for ordering).

### 4.1 Event type catalog

**`session_started`**
```json
{
  "session_id": "uuid",
  "problem_domain": "coding" | "math" | "writing" | "general_reasoning",
  "problem_text": "string",
  "created_at": "iso8601"
}
```

**`attempt_submitted`**
```json
{
  "session_id": "uuid",
  "attempt_text": "string",
  "text_length": "int",
  "time_since_session_start_ms": "int",
  "is_partial": "bool"
}
```
Note: `is_partial=true` allowed — the gate should accept "I don't know where to start, but here's my thinking" as a valid attempt. Forcing a complete answer before unlocking AI would break the "not controlling" principle.

**`attempt_skipped`**
```json
{
  "session_id": "uuid",
  "time_since_session_start_ms": "int",
  "skip_reason": "string | null"
}
```
This event is just as important as `attempt_submitted` — it's the honest alternative to forcing engagement, and it's a first-class data point (this session is unambiguously AI-first).

**`ai_hint_requested`**
```json
{
  "session_id": "uuid",
  "tier_requested": 1 | 2 | 3,
  "time_since_session_start_ms": "int",
  "preceded_by_attempt": "bool"
}
```

**`ai_hint_delivered`**
```json
{
  "session_id": "uuid",
  "tier": 1 | 2 | 3,
  "hint_text": "string",
  "model_latency_ms": "int"
}
```

**`verification_submitted`**
```json
{
  "session_id": "uuid",
  "matches_own_attempt": "bool | null",
  "justification": "string",
  "time_since_hint_delivered_ms": "int"
}
```

**`evaluation_submitted`**
```json
{
  "session_id": "uuid",
  "makes_sense": "bool",
  "reasoning": "string"
}
```

**`session_closed`**
```json
{
  "session_id": "uuid",
  "total_duration_ms": "int",
  "ai_events_count": "int",
  "final_status": "solved_independently" | "solved_with_ai" | "abandoned"
}
```

### 4.2 Ordering and integrity rules

- `created_at` is always set server-side on insert, never trusted from client payload — prevents any possibility of a client backdating an event to game its own derived metrics.
- Every event except `session_started` must reference a valid, still-open `session_id` — the API rejects orphaned events (fault-tolerance rule, see Part 12).
- No event type is ever deleted. If a bug produces a bad event, a corrective event is inserted (e.g., `event_invalidated` referencing the bad `event_id`), and downstream ETL filters invalidated events — the raw log is permanently append-only.

---



## Implementation contract extensions (before implementation)

All event envelopes contain server-assigned user_id, session_id, created_at, and a UUID event_id. POST /events accepts only {event_id, session_id, event_type, payload}; authoritative duration/count/length fields are computed by the server. Unknown fields/types are rejected. Session ID is carried in the envelope and added to stored payloads. Internal service events are not accepted from clients.

| Event | Input payload | Traceability |
| --- | --- | --- |
| attempt_submitted | attempt_text (1–20000 chars), is_partial bool | #3; text length and elapsed time derived |
| attempt_skipped | skip_reason nullable string | #1/#10; elapsed time derived |
| verification_submitted | hint_event_id UUID, matches_own_attempt nullable bool, justification (1–5000 chars) | #4; ties verification to delivery; delay derived |
| verification_skipped | hint_event_id UUID | #4/#10; explicit opt-out |
| evaluation_submitted | makes_sense bool, reasoning (1–5000 chars) | #7 |
| evaluation_skipped | empty object | #7/#10 |
| attempt_correctness_reported | attempt_event_id UUID, adequate bool | #5, explicit self-reported adequacy |
| event_invalidated | target_event_id UUID, reason string | integrity correction; admin-only, cannot target lifecycle/invalidation events |
| hint_tier_violation | tier int, reason string, provider_response string | internal #10 guardrail |
| ai_hint_failed | request_event_id UUID, reason string | internal integrity; distinguishes requests from responses |

POST /sessions takes {event_id, problem_domain, problem_text}; creates session_started with server timestamp. POST /sessions/{id}/close takes {event_id, final_status}; creates session_closed with server duration/count. POST /ai/hint takes {event_id, session_id, tier}; its idempotent request transaction logs ai_hint_requested, then ai_hint_delivered or ai_hint_failed. A failed operation remains a request in analytics; retry a failure deliberately with a new event_id. Automatic provider fallback now follows the extension below, within the same logical request. Hint tiers progress 1 → 2 → 3 and verification or a logged skip precedes escalation. ai_hint_delivered additionally references request_event_id; timestamps and ordering always originate on the server.

## Failure recovery outcome (2026-09-15)

`session_closed.final_status` additionally permits `solved_without_ai_response` (constructs #1/#6 and failure integrity). It means the participant reports completion after at least one AI request but no delivered AI responses. The server rejects this status if a hint was delivered or no AI request exists. This fixes completion after configuration/provider failures without mislabeling the session as zero-AI-request completion. `no_ai_completion_rate` continues to require zero AI requests. No new event type or metric is introduced.

## User-requested provider support (2026-09-15)

The user selected Google Gemini, Groq, and OpenRouter instead of Claude. This is an implementation substitution for traceability #10, not a new research feature. POST /ai/hint accepts an optional `provider`: `gemini`, `groq`, `openrouter`, or legacy `anthropic`. Omission uses server `AI_PROVIDER`. Arbitrary models, prompts, and API URLs are never accepted from the client. The server adds `provider` and configured `model` to ai_hint_requested/ai_hint_failed/hint_tier_violation. ai_hint_delivered includes `provider`, configured `model`, and `reported_model` from the provider response (nullable if absent). Legacy events without these fields remain valid. Retries cannot change the provider for an existing event ID. This initial provider design has been superseded by the automatic fallback extension below. OpenRouter may also route internally, and its reported model is retained for research provenance.

## Automatic fallback and continued discussion (user-authorized)

The user explicitly requested seamless automatic fallback across Groq, Gemini, OpenRouter, Mistral AI, and Cloudflare. This supersedes earlier no-automatic-fallback decisions. Cloudflare means Workers AI; it requires CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID. `mistral`, `cloudflare`, and `auto` are accepted provider selectors. Automatic routing preserves the same tier and conversation context, without exposing intermediate failures in the conversation.

`ai_provider_attempted` is an internal-only event (#10 and integrity), containing request_event_id, attempt_index, provider, model, outcome (`success`, `failed`, `skipped`), error_code nullable string, latency_ms, and retry_after_seconds nullable number. It logs every fallback attempt or cooldown/configuration skip; it never contributes to ai_requests metrics. Tier overshoots additionally produce hint_tier_violation referencing request_event_id. One user action still creates exactly one ai_hint_requested and at most one ai_hint_delivered or final ai_hint_failed. Final delivery records the successful provider/model and reported_model. No partial output from a failed provider is presented as a complete answer. If every eligible provider fails, the request remains saved and a retryable final error is shown.

`POST /ai/hint` additionally accepts `followup_text` (optional 1–5000 characters, tier 3 only, after the full explanation was delivered). Server-owned ai_hint_requested payload adds request_kind (`hint` or `followup`) and followup_text (nullable), plus fallback_enabled. Follow-up replies use the same delivered/verification events, so usage and verification ratios continue to include every user AI request. The conversation is bounded to the latest 12 messages / 24000 characters in model context, while the complete original timeline remains stored. The problem and latest saved attempt are always provided. This is continued discussion of the session problem (#4/#7/#10), not an unrelated general chat product.

Evaluation applies to the most recent delivered AI response. A new response requires a new evaluation or explicit skip at closure; prior evaluations remain in the log. `GET /ai/requests/{event_id}` reports owned pending/completed/failed requests, resolving expired requests through existing ai_hint_failed events. It never starts a new provider call.

## Phase 1: everyday conversations (2026-09-16)

The latest user direction authorizes immediate answers with optional independent practice. New web sessions explicitly send `experience: chat` and `initial_mode: ask_ai | try_myself` to POST /sessions. These fields are recorded in session_started, with protocol_version `chat-v1`. Omitted experience remains `guided` for existing API clients and historical study sessions, with protocol_version `guided-v1`. Idempotency checks include experience and initial_mode. Missing fields on historical events mean guided/ask_ai.

`conversation_mode_changed` is a client-emittable event with payload `{mode: ask_ai | try_myself}` and belongs to behavioural context/integrity. The API accepts it only for open chat sessions. It never implies that an attempt occurred. GET /sessions/{id} exposes experience and the most recently recorded mode. Reconstruction exposes experience and initial_mode; guided-v1 and chat-v1 are distinct protocols and must be identified in research comparisons.

For chat sessions, POST /ai/hint retains the existing idempotency, ownership, persistence and fallback machinery. Tier 3 means a direct answer; tiers 1/2 mean explicitly requested limited help. No attempt gate, forced ladder, verification gate or mandatory final evaluation applies. After the first delivered response, further requests require followup_text to distinguish the user's intent. A follow-up can request an answer or a hint at any tier. Requests record `experience`, `mode`, and request_kind (`answer`, `hint`, or `followup`); deliveries preserve those attributes. Guided sessions retain their previous rules. Missing verification is missing data, not an invented verification_skipped event.

Navigation away from an everyday conversation leaves it open. Explicitly completing a chat remains an optional action and preserves the existing truthful final statuses. Session summaries retain the full raw timeline. New chat response-rate statistics may be computed, but comparison with guided sessions requires separate protocol selection; mode choice is not a diagnosis of AI dependence.

Research endpoints and the export CLI default to experience `guided`; selecting `chat` explicitly analyses the everyday protocol. They do not silently pool the two protocols. JSON exports identify the selected experience and CSV downloads use a protocol-specific filename. Historical events remain unmodified.
# Phase 2: usage and answer length

`POST /ai/hint` accepts `answer_style: concise | detailed` (default `concise`). The value is persisted on requested/delivered events and participates in request-ID conflict checks. Existing requests without this field are treated as concise for retry compatibility.

`ai_provider_attempted.payload.usage` and `ai_hint_delivered.payload.usage` contain provider-reported `input_tokens`, `output_tokens`, `total_tokens`, `reasoning_tokens`, `cached_input_tokens`, and `cost_micro_usd` where available. Missing values are `null`, not zero. OpenAI-compatible output totals include reasoning; Gemini total includes its separately reported thoughts. Failed generation attempts retain usage when a response supplied it. Skipped providers are not billable attempts.

Accounting uses new `ai_usage_requests` and `ai_budget_lock` tables without modifying historical events or session schemas. The ledger is mutable operational state; behavioral events remain append-only. Admission and request insertion commit together. Rejected admission returns HTTP 429 with no AI request event, no allowance charge, and no provider call. An admitted request consumes one daily allowance even if all providers fail. Fallback attempts do not inflate logical request counts. GET `/ai/usage` is participant-scoped; workspace totals require administrator access or development mode. See [AI usage controls](ai-usage.md) for reservation, expiry, and dollar-estimate semantics.

## Phase 3: optional practice and feedback

`practice_invitation_responded` has `answer_event_id` (a delivered answer in the same chat) and `decision` (`try_myself` or `continue_ai`). Eligibility is computed on the server. The first decision for an invitation wins across tabs; exact event-ID retries remain idempotent. Yes also appends `conversation_mode_changed` with source `practice_invitation` and the decision's event ID in the same transaction. It does not create an attempt or verification.

`answer_feedback` has `answer_event_id` and `rating` (`helpful`, `not_helpful`, `cleared`). Latest feedback wins; previous events remain immutable. This event alone may be added to a completed chat without changing its status. Feedback is not a correctness assessment and does not count as research verification.

A separate `user_preferences` table stores the participant's `practice_reminders` boolean. Authenticated GET/POST `/preferences` expose only the caller's preference. GET `/sessions/{id}` includes `practice` eligibility, an invitation anchor, an active practice task, and the reminder preference. See [practice support](practice-support.md) for thresholds and retry behavior.

## Phase 4: history, progress and optional AI reviews

`GET /history` is owner-scoped with literal `q` search (up to 200 characters), `status=all|open|completed|abandoned`, `experience=all|chat|guided`, `limit=1..50` and non-negative `offset`. It returns items, total, limit, offset and has_more. Searches ignore invalidated events. `POST /sessions/{id}/title` sets a trimmed title of 1–100 characters, or null to restore the derived title. Metadata is stored separately from the immutable original question.

`GET /progress?experience=chat|guided` returns separate all-time totals, observed work combinations, and four weekly activity buckets. The default is chat; protocols are never pooled here. `GET /sessions/{id}` adds title/custom_title and an overview with factual counts and a source fingerprint.

Explicit review requests use `POST /sessions/{id}/analysis` with event_id and session_id; `GET /ai/analyses/{event_id}` polls only the authenticated owner's request. `ai_analysis_requested`, `ai_analysis_provider_attempted`, `ai_analysis_delivered`, and `ai_analysis_failed` are server-owned events. Delivery records its request ID, text, source_fingerprint, excerpts_truncated, provider/model and reported usage. Request-ID replay is idempotent; an existing successful review of the same source is reused without charging another allowance. Titles, mode toggles, feedback, prior reviews and closing a chat do not invalidate an unchanged review source.

AI reviews use the shared allowance ledger and conservative fallback reservations. They are not answer/hint events, do not enter practice streaks or verification denominators, and do not reopen completed chats. Guided study sessions cannot request them. Bounded input uses at most 24 recent text excerpts and 16,000 excerpt characters, plus up to 2,000 original-question characters if the original question fell outside that window. The model is told when context is incomplete and instructed not to score intelligence, dependence or cognitive health.


## Privacy maintenance exception

Privacy choices and deletion requests use separate account tables, not invented behavioral events. Existing records are not implicitly consented into research. Ordinary event writes remain append-only. An authorized conversation-erasure request may be fulfilled only by the offline operator command, with transactional trigger suspension and restoration; it removes the complete targeted conversation history rather than fabricating a correction event. Account identity, request audit, and quota accounting remain. See [privacy](privacy.md) and [operator runbook](operations.md).


## Current-question help actions

New chat AI request/answer payloads include optional `help_action` (`hint` or `answer`) and server-resolved `focus_question`. A help action does not establish a new subject. Explicit follow-up messages do. The latest independent attempt after that question is the current attempt; earlier work remains chronological background. Older generated button phrases are recognized without rewriting their stored events. Request replay checks help intent as well as question, tier, provider and answer length. Guided study retains its original hint protocol.
