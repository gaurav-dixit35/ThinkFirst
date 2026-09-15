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
