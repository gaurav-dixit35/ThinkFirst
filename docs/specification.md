# ThinkFirst — Complete Project Specification
### A Behavioral-Logging Extension of "Human Problem-Solving Behavior in the Age of Generative AI"

Version 1.0 — Master build document for development (Codex + human team)

---

## PART 0 — HOW TO USE THIS DOCUMENT

This is the single source of truth for the project. It is organized so that:

- **Section 1** explains *why* the project exists and what it must never drift into.
- **Section 2** is the traceability matrix — every feature maps to a specific line in the research paper. If a feature isn't in this table, it doesn't belong in the MVP.
- **Section 3–9** are the technical specification: architecture, schema, API, AI logic, design system, analytics pipeline.
- **Section 10** is the phase-by-phase build plan broken down to ticket level.
- **Section 11** is the non-negotiables list — hand this to Codex verbatim.
- **Section 12** is the risk register and fault-tolerance rules.
- **Section 13** is the glossary connecting research language to code language.

Whenever there is a conflict between "what feels like a good feature" and "what's in the traceability matrix," the traceability matrix wins. This document exists to prevent scope drift.

---

## PART 1 — PROJECT THESIS

### 1.1 The one-sentence thesis

> The research paper measured AI-first problem-solving behavior using a 10-question self-report survey at a single point in time. This project builds the instrument that measures the same five behavioral constructs continuously and objectively, through logged interaction events instead of Likert-scale self-report, and re-runs the paper's own statistical tests (Spearman correlation, Mann–Whitney U, binary logistic regression) on that real behavioral data.

### 1.2 Why this framing, specifically

The paper's own **Limitations** section (Section IX-A) names two structural weaknesses:

1. **Cross-sectional design** — data collected at one point in time, so no ability to observe behavior developing or changing.
2. **Self-reported data** — behavior is inferred from what people *say* they do, not what they *actually* do.

A project that is "an AI tutor with some hint levels" does not address either weakness. A project that **logs the exact five constructs as timestamped events, longitudinally, per user** directly answers both. This is the difference between "a nice app" and "a second study." Keep this framing in every conversation about the project — with your guide, with judges, with Codex.

### 1.3 The tension to resolve explicitly (read this twice)

You asked for two things that are in tension if not handled carefully:
- The system should discourage AI-first behavior and encourage independent thinking first.
- The user should never feel controlled or nagged.

**Resolution rule, non-negotiable:** Every friction mechanism must be:
- **Visible** — the user always knows why a delay/step exists ("Try your own approach first — takes 30 seconds, totally optional").
- **Skippable** — skipping is always possible in one click, and skipping is itself logged as data, not blocked as a bug.
- **Explained, never hidden** — no dark patterns, no disguised delays, no shame-based copy.

This is what makes it "classy" instead of "naggy" — the system informs and invites, it never traps.

### 1.4 What the project is NOT

- It is **not** a general-purpose ChatGPT wrapper.
- It is **not** a plagiarism/cheating detector.
- It is **not** making a moral claim that "AI is bad." The paper explicitly refuses that framing (Section VII-F, VIII) and so must the project's copy and behavior.
- It is **not** trying to be a commercial product in v1. It is a research instrument first, a product-shaped prototype second.

---

## PART 2 — RESEARCH-TO-FEATURE TRACEABILITY MATRIX

This table is the spine of the whole project. Every feature must trace to a row here.

| # | Research Construct (Paper Section) | Original Measurement (Survey) | Project's Behavioral Equivalent | Logged Event(s) | Derived Metric |
|---|---|---|---|---|---|
| 1 | AI-first behavior (Q: "first action when encountering a problem") — Fig. 2, 68.97% AI-first | Single-choice question, self-reported at survey time | Whether user requests AI help *before* submitting any independent attempt in a session | `problem_started`, `attempt_submitted` (or absence of it), `ai_hint_requested` | `is_ai_first = ai_hint_requested.timestamp < attempt_submitted.timestamp` (or attempt never submitted) |
| 2 | AI usage frequency (Q1, Table 2) | 5-point frequency scale ("several times a day"→"rarely") | Count and cadence of `ai_hint_requested` events per user per week | `ai_hint_requested` | Rolling 7-day and 30-day request count |
| 3 | Independent reasoning before AI (Q6, Table 3, M=1.969) | 5-point Likert agreement | Whether/how much the user writes before requesting AI; time spent before first AI request | `attempt_submitted` (with `text_length`, `time_since_problem_started`) | `attempt_effort_score` (normalized combination of length + time) |
| 4 | Verification of AI-generated information (Q7, Table 3, M=2.268) | 5-point Likert agreement | Explicit required step: does the AI answer match your own attempt, and why | `verification_submitted` (fields: `matches_own_attempt: bool`, `justification: string`) | `verification_rate = verifications_submitted / ai_responses_received` |
| 5 | AI reliance despite being able to solve independently (Q8, Table 3, M=3.854 — highest mean, strongest tendency) | 5-point Likert agreement | Detecting when a user's own attempt was substantively correct/complete but they requested AI anyway | `attempt_submitted` + `ai_hint_requested` + later self/peer correctness signal | `unnecessary_ai_use_flag` (attempt scored adequate AND ai still requested) |
| 6 | Confidence in solving without AI (Q9, Table 3, M=2.241) | 5-point Likert agreement | Rate of sessions where the user completes the problem with zero AI events | `session_closed` (with `ai_events_count`) | `no_ai_completion_rate` |
| 7 | Evaluation of AI answers ("does this make sense?") (Q10, Table 3, M=2.253) | 5-point Likert agreement | Required structured reflection before closing a session that used AI | `evaluation_submitted` (fields: `makes_sense: bool`, `reasoning: string`) | `evaluation_completion_rate`, qualitative reasoning corpus |
| 8 | AI-first ↔ AI usage frequency association (H1, OR=2.114, p<0.001) | Logistic regression on survey data | Same regression, run on logged `is_ai_first` (dependent var) vs. rolling AI usage frequency (independent var) | derived from #1 and #2 | Live-updating odds ratio per cohort |
| 9 | AI-first vs. non-AI-first group differences (H2–H6, Mann–Whitney, Table 5) | Group comparison on Likert scores | Same test structure, comparing derived metrics #3–#7 between users/sessions flagged `is_ai_first=true` vs. `false` | all of the above | Live Mann–Whitney U statistics, rank-biserial effect sizes |
| 10 | "AI-assisted, not AI-first" design implication (Section VIII) | Stated as a recommendation, not implemented | The literal core UX of the app: gated, tiered AI assistance | all gating events | N/A — this is the product, not a metric |

**Rule for Codex and for you:** before adding any new feature, find its row in this table. If there isn't one, either add the row with a clear justification, or don't build the feature yet.

---

## PART 3 — SYSTEM ARCHITECTURE (DETAILED)

### 3.1 High-level component diagram (textual)

```
┌────────────────────────────────────────────────────────────────┐
│  CLIENT — Next.js 14 (App Router) + TypeScript + Tailwind        │
│                                                                    │
│  [Problem Intake] → [Attempt Editor] → [AI Request Gate]         │
│        → [Tiered Hint Panel] → [Verification Step]               │
│        → [Evaluation Step] → [Session Summary]                   │
│                                                                    │
│  Separately: [Personal Dashboard] [Settings] [Auth]               │
└───────────────────────────┬────────────────────────────────────┘
                             │ REST calls (typed via shared schema)
┌───────────────────────────▼────────────────────────────────────┐
│  API — FastAPI (Python 3.11+)                                    │
│                                                                    │
│  /events           POST — validate & persist any event           │
│  /sessions          GET/POST — session lifecycle                  │
│  /ai/hint           POST — tiered hint request (gated server-side)│
│  /analytics/me       GET — personal rollups for dashboard          │
│  /analytics/research  GET (admin) — aggregate stats export         │
│  /auth/*            — session/user management (Clerk/Auth.js)     │
└───────┬──────────────────────┬───────────────────┬───────────────┘
        │                      │                    │
┌───────▼────────┐   ┌─────────▼─────────┐  ┌───────▼─────────────┐
│ Postgres         │   │ Claude API         │  │ Redis (optional,     │
│ - events (append)│   │ (hint generation,  │  │ Phase 7+)             │
│ - users           │   │ backend-controlled │  │ per-user EWMA cache   │
│ - session_rollups │   │ tier logic)        │  │                       │
│ (materialized)     │   └────────────────────┘  └───────────────────────┘
└───────┬────────────┘
        │ nightly / on-demand ETL
┌───────▼────────────────────────────────────────────────────────┐
│  ANALYTICS ENGINE — Python (pandas, scipy, statsmodels)           │
│  Reads raw events → builds analysis dataframe → runs:             │
│   - Spearman correlation matrix (mirrors paper's Fig. 3)          │
│   - Mann–Whitney U, AI-first vs non-AI-first (mirrors Table 5)     │
│   - Binary logistic regression (mirrors Table 6)                   │
│  Outputs: JSON for dashboard + CSV/notebook for research write-up  │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Why these specific choices (so Codex doesn't second-guess them)

- **Postgres, append-only `events` table, not a mutable "user_state" document store.** The research value of this project depends on being able to reconstruct exact session timelines later, the same way you'd reconstruct a participant's response pattern. An append-only event log is the only structure that guarantees this. Never `UPDATE` an event row — corrections are new events (e.g., `attempt_edited`), never in-place mutations.
- **FastAPI (Python), not Node, for the backend.** The analytics engine (Part 8) is written in Python using the same libraries named in the paper's own methodology (pandas, scipy, statsmodels — see Section VI-F of the paper). Keeping backend and analytics in the same language means the ETL job can literally import backend models directly, with zero serialization boundary or duplicate schema maintenance.
- **Materialized rollup tables, not "compute on every page load."** The dashboard (Phase 5) and the gating engine (Phase 7) both need fast reads of "this user's recent behavior summary." Recomputing from raw events on every request doesn't scale past a handful of users and adds latency to the gate itself — which must feel instant.
- **Claude API with backend-enforced tiering, not "just ask the model to give hints."** If tier control lives only in the system prompt, a slightly different phrasing of the user's question can leak a full answer at tier 1. The backend must literally choose what request to send to the model per tier (see Section 6.3) — the model never sees "give me a small hint," it only ever sees the specific constrained request for that tier.

---

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

## PART 5 — DATABASE SCHEMA (DDL)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    problem_domain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open', -- open | closed
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID NOT NULL REFERENCES sessions(id),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    invalidated_by UUID REFERENCES events(id) DEFAULT NULL
);
CREATE INDEX idx_events_session ON events(session_id, created_at);
CREATE INDEX idx_events_user_type ON events(user_id, event_type, created_at);

-- Materialized rollup, refreshed nightly or on-demand
CREATE MATERIALIZED VIEW user_behavior_rollup AS
SELECT
    user_id,
    count(*) FILTER (WHERE event_type = 'ai_hint_requested') AS ai_requests_total,
    count(*) FILTER (WHERE event_type = 'attempt_submitted') AS attempts_total,
    count(*) FILTER (WHERE event_type = 'verification_submitted') AS verifications_total,
    -- ai_first sessions computed via a helper query per session, aggregated here
    now() AS refreshed_at
FROM events
GROUP BY user_id;
```

This schema is intentionally minimal for v1 — resist the urge to add speculative columns. Every additional column needs a row in the Part 2 traceability matrix first.

---

## PART 6 — AI ORCHESTRATION LOGIC (TIERED HINTS)

### 6.1 The core rule

The frontend never has the ability to request "the answer." It can only request `tier: 1`, `tier: 2`, or `tier: 3`. The backend decides what prompt to send to Claude for each tier — the frontend's request is a *level*, not a *prompt*.

### 6.2 Tier definitions

| Tier | Name | What it contains | Backend prompt strategy |
|---|---|---|---|
| 1 | Clarify | A question back to the user, or a restatement of the problem highlighting the key constraint | System prompt instructs Claude to respond *only* with a clarifying question or a reframing — explicitly instructed not to solve anything |
| 2 | Partial | One concrete next step or a relevant concept/formula, without applying it to the specific problem | System prompt provides the user's own attempt text as context and asks for "the single most useful next step," capped at ~40 words |
| 3 | Full | Complete explanation/solution | Full context (problem + user's attempt + prior hints) sent, unrestricted response |

### 6.3 Why backend-enforced, not prompt-only

A user can phrase a "tier 1 clarifying request" in a way that convinces a model to just answer directly if the *only* constraint is prompt wording. So: at tier 1 and 2, the backend truncates/validates the model's response server-side against simple heuristics (e.g., tier-1 response must end in a question mark or be under N tokens) before forwarding to the client, and logs a `hint_tier_violation` internal event if the model overshoots — this is monitored, not silently "fixed" by regenerating (regenerating silently hides a real failure mode from your own analytics).

### 6.4 Hint ladder UX rule

Each tier must be explicitly requested by a visible button click ("Show a bigger hint") — never auto-escalated. Auto-escalating without a click is the single fastest way to slide from "gentle nudge" into "controlling," so it's disallowed by design.

---

## PART 7 — FRONTEND COMPONENT ARCHITECTURE

```
apps/web/
├── app/
│   ├── session/[id]/page.tsx        # main problem-solving flow
│   ├── dashboard/page.tsx            # personal analytics
│   ├── history/page.tsx              # past sessions list
│   └── (auth)/...                    # login/signup
├── components/
│   ├── ProblemIntake.tsx
│   ├── AttemptEditor.tsx             # rich text or code editor depending on domain
│   ├── AIRequestGate.tsx             # the friction UI — countdown/explainer + skip
│   ├── HintLadder.tsx                # tier 1/2/3 buttons + response display
│   ├── VerificationStep.tsx
│   ├── EvaluationStep.tsx
│   ├── SessionSummary.tsx
│   └── dashboard/
│       ├── AIFirstRatioChart.tsx
│       ├── VerificationRateChart.tsx
│       └── TimeToAIChart.tsx
├── lib/
│   ├── eventClient.ts                # single function: emitEvent(type, payload) — every component calls only this, never fetch() directly
│   └── api.ts
└── styles/
    └── tokens.css                    # design tokens, defined Phase 0, applied Phase 8
```

**Non-negotiable frontend rule:** all event emission goes through one function, `emitEvent()`, which handles retries, offline queuing, and error surfacing centrally. No component should call `fetch('/events')` directly — this is the single point where "no fault tolerance" (Part 12) is enforced.

---

## PART 8 — ANALYTICS / ETL PIPELINE (MIRRORS THE PAPER'S OWN METHODOLOGY)

### 8.1 Pipeline stages

1. **Extract:** pull raw `events` rows for a given date range.
2. **Transform (session reconstruction):** group events by `session_id`, reconstruct ordered timeline, compute derived fields per session (`is_ai_first`, `attempt_effort_score`, `verification_rate` contribution, etc.) — this stage literally implements the "Derived Metric" column of Part 2's matrix.
3. **Transform (user aggregation):** roll session-level data up to per-user summary statistics — mirrors the paper's per-respondent structure (Table 1–3).
4. **Analyze:**
   - `scipy.stats.spearmanr` across the same variable set as the paper's Fig. 3 heatmap.
   - `scipy.stats.mannwhitneyu` comparing `is_ai_first=True` vs `False` groups on the five derived indicators — mirrors Table 5 exactly, including rank-biserial effect size.
   - `statsmodels.api.Logit` for AI usage frequency → AI-first likelihood — mirrors Table 6, same odds-ratio reporting format.
5. **Load:** write results to a `research_exports` table (JSON) for the dashboard, and export a CSV + a Jupyter notebook reproducing the paper's exact table formats for your own report/demo.

### 8.2 This is your demo moment

In a live demo or report, running this pipeline on your own logged usage and placing the output table side-by-side with the paper's Table 5 is the single strongest piece of evidence that the project is a genuine extension of the research, not a bolt-on app. Build this pipeline early enough (Phase 6) that you have real output before your presentation date — don't leave it for the last week.

---

## PART 9 — DESIGN SYSTEM ("CLASSY, ELEGANT, USER-FRIENDLY")

Since "classy" is subjective, here is a concrete, defensible default direction — treat it as a strong starting proposal, adjust once you give me 2–3 reference sites you like:

- **Typography:** one serif display face for headings (e.g., a humanist serif like Source Serif or Newsreader) + one clean sans for body/UI (Inter or IBM Plex Sans). Serif headings signal "thoughtful/academic," which fits a reflection-oriented product.
- **Color:** a muted, warm neutral base (off-white, warm gray) with a single confident accent color used sparingly (for the "Ask AI" unlock state and dashboard highlights only) — avoid the generic "AI product" palette of electric purple/blue gradients. This product's visual identity should feel calm, not techy/flashy, because the message is "slow down," not "move fast."
- **Motion:** minimal, purposeful only — a soft fade when a hint tier unlocks, no bouncing/celebratory animations for AI usage (celebrating AI use undercuts the thesis).
- **Microcopy tone:** collaborative and non-judgmental everywhere. Examples:
  - Gate: *"Give it your own shot first — even a rough idea helps. You can skip if you'd rather not."*
  - Skip button: plain *"Skip, ask AI now"* — never guilt-worded ("Skip (not recommended)" is already too much).
  - Verification step: *"Does this match what you were thinking? A quick note helps you remember your reasoning later."*
- **Empty/loading/error states:** every screen has all three explicitly designed before Phase 8 is considered done — this is part of "no fault tolerance," not just aesthetics.

---

## PART 10 — PHASE-BY-PHASE BUILD PLAN (TICKET LEVEL)

### Phase 0 — Foundation
- [ ] Write `docs/event-schema.md` (copy Part 4 of this doc verbatim as the starting point)
- [ ] Scaffold `apps/web` (Next.js 14, TS, Tailwind)
- [ ] Scaffold `apps/api` (FastAPI, Pydantic models matching event schema)
- [ ] Local Postgres via Docker Compose
- [ ] One health-check round trip: frontend button → API → DB insert → DB read → frontend confirmation
- [ ] Define `tailwind.config` tokens (colors, fonts) from Part 9, unused until Phase 8

### Phase 1 — Event Spine
- [ ] `events` table + migration (Part 5 DDL)
- [ ] `POST /events` endpoint: validates `event_type` against schema, rejects unknown types (400, not silent drop)
- [ ] `emitEvent()` client function with retry + offline queue (localStorage buffer, flush on reconnect)
- [ ] Integration test: emit all 8 event types, confirm correct persistence and ordering by `created_at`

### Phase 2 — Core Flow UI
- [ ] `ProblemIntake` component → emits `session_started`
- [ ] `AttemptEditor` (plain textarea for v1, domain-aware editor later) → emits `attempt_submitted` or `attempt_skipped`
- [ ] `AIRequestGate` — shows explainer copy, skip button, unlocks hint ladder → this is where the "visible, skippable, explained" rule from Part 1.3 is implemented and must be reviewed against that rule explicitly before moving on
- [ ] `session_closed` emitted on navigation away / explicit "I'm done" button

### Phase 3 — AI Orchestration
- [ ] Backend tier-specific prompt templates (Part 6.2)
- [ ] `POST /ai/hint` — accepts `{session_id, tier}`, returns hint text, emits `ai_hint_requested` + `ai_hint_delivered` server-side (never trust client to log this)
- [ ] Tier-1/2 response validation heuristic + `hint_tier_violation` internal logging
- [ ] `HintLadder` component wired to real API

### Phase 4 — Verification Loop
- [ ] `VerificationStep` component → emits `verification_submitted`
- [ ] `EvaluationStep` component → emits `evaluation_submitted`
- [ ] Session cannot reach `session_closed` with status `solved_with_ai` unless both steps are present OR explicitly skipped-and-logged (skipping here is also allowed per Part 1.3, but tracked distinctly)

### Phase 5 — Personal Analytics
- [ ] `user_behavior_rollup` materialized view + refresh job
- [ ] `GET /analytics/me` endpoint
- [ ] Dashboard charts: AI-first ratio trend, verification rate, time-to-AI trend (Recharts)

### Phase 6 — Research Pipeline
- [ ] `analytics/etl.py` — extract/transform per Part 8.1
- [ ] `analytics/stats.py` — Spearman, Mann-Whitney, logistic regression functions, output formatted to mirror paper's Tables 5/6
- [ ] `research_exports` table + `GET /analytics/research` (admin-only)
- [ ] Notebook or script producing a side-by-side comparison table against the paper's actual published numbers

### Phase 7 — Adaptive Friction (stretch)
- [ ] Per-user EWMA of AI-first tendency (Redis cache, nightly recompute)
- [ ] Gate intensity parameter (delay length, copy variant) driven by EWMA score
- [ ] A/B-style internal logging to confirm the adaptive gate doesn't just become "more nagging" — track skip-rate as a canary metric; rising skip-rate = friction miscalibrated

### Phase 8 — Design Polish
- [ ] Apply Part 9 tokens across all components
- [ ] Empty/loading/error state for every screen
- [ ] Motion pass (Framer Motion, minimal)
- [ ] Full copy review against the microcopy tone rules

### Phase 9 — Hardening + Deploy
- [ ] Auth integration (Clerk or Auth.js)
- [ ] Try/catch + user-facing fallback on every async call, no silent failures (Part 12)
- [ ] Unit tests: event validation, stats functions (these must never silently produce wrong numbers)
- [ ] Deploy: Vercel (web) + Railway/Render (api + Postgres)
- [ ] Smoke test full flow in production

---

## PART 11 — NON-NEGOTIABLES (HAND TO CODEX VERBATIM)

1. **Event schema is law.** Never invent a new event type or field without updating `docs/event-schema.md` first.
2. **Append-only events. No `UPDATE` or `DELETE` on the `events` table, ever.** Corrections are new events referencing the old one.
3. **Server-authoritative timestamps.** Never trust a client-provided `created_at`.
4. **Every friction mechanism must be visible, skippable, and explained.** No dark patterns, no auto-escalation without a user click, no guilt-worded skip buttons.
5. **AI tier control is backend-enforced, not prompt-only.** The frontend requests a tier number, never a prompt.
6. **No silent failures.** Every async call has a try/catch and a real user-facing fallback state. A failed event emission must visibly queue/retry, never disappear.
7. **UI polish happens in Phase 8, not before.** Do not spend time on visual design before the event spine and core flow work end-to-end.
8. **Every feature must map to a row in the Part 2 traceability matrix.** If it doesn't, flag it for discussion before building.
9. **The analytics pipeline (Part 8) must use the same statistical methods and reporting format as the paper** (Spearman, Mann-Whitney with rank-biserial effect size, binary logistic regression with odds ratios and CIs) — this is what makes the output comparable and citable.

---

## PART 12 — RISK REGISTER & FAULT-TOLERANCE RULES

| Risk | Mitigation |
|---|---|
| Client loses connection mid-session, events lost | `emitEvent()` buffers to localStorage, flushes on reconnect; session reconstruction tolerates gaps but flags them |
| Model (Claude) returns a full answer at tier 1 despite prompt constraints | Server-side heuristic validation + `hint_tier_violation` logging (monitored, not hidden) |
| Materialized view goes stale, dashboard shows wrong numbers | Refresh timestamp always shown to user ("Updated 3 minutes ago"); never silently show stale data as current |
| Analytics pipeline silently produces wrong stats due to a schema drift | Unit tests on the ETL transform layer with fixed known-input/known-output cases (golden tests), run in CI before any deploy |
| A user's single bad event corrupts an aggregate metric | Every derived metric computation has bounds/sanity checks (e.g., a session duration of negative time is impossible — flagged and excluded, not averaged in) |
| Friction feature starts feeling "controlling" as it's tuned | Skip-rate tracked as a canary metric from day one; a rising skip-rate is treated as a UX bug, not a success metric |

---

## PART 13 — GLOSSARY: RESEARCH LANGUAGE → CODE LANGUAGE

| Paper term | Code/system term |
|---|---|
| AI-first problem-solving behaviour | `is_ai_first` boolean, derived per session |
| Independent reasoning before AI assistance | `attempt_effort_score` from `attempt_submitted` |
| Verification of AI-generated information | `verification_submitted` event + `verification_rate` |
| AI reliance (use despite being able to solve independently) | `unnecessary_ai_use_flag` |
| Confidence without AI | `no_ai_completion_rate` |
| Evaluation of AI answers | `evaluation_submitted` event |
| AI usage frequency | rolling count of `ai_hint_requested` |
| Respondent | `user` |
| Survey response | `session` |
| Likert scale (1–5 agreement) | continuous/derived metric from logged behavior (no scale — this is the core improvement) |

---

*End of specification. Hand Part 4, Part 5, Part 10, and Part 11 to Codex as the literal build instructions. Keep this whole document open as the reference for every design decision along the way.*