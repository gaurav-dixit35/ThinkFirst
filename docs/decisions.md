# Implementation decisions and traceability

The master specification is preserved in `specification.md`. Phase 7 is explicitly a stretch feature and is deferred. The original local research MVP exists; the updated consumer product phases are tracked separately in roadmap.md. Cloud deployment requires operator accounts and secrets.

* User steering on 2026-09-15 prioritizes functional work before further visual polish and replaces the Claude-only requirement with Gemini, Groq, and OpenRouter. An optional preferred provider can be chosen in the session. Prompts, model configuration, keys and URLs remain backend-owned. The request logs the chosen provider/model and delivery logs the reported model. OpenRouter's own routing may select an underlying model; the latest user instruction authorizes automatic switching between configured services; every internal attempt and the actual answering service are logged. Legacy Claude sessions remain readable.
* An AI request that failed to deliver no longer blocks a participant from reporting completion. `solved_without_ai_response` preserves the request history and does not increase the zero-AI-request completion metric.

* Security maintenance exception: Next.js 14.2.35 has critical advisories in the current npm audit, including GHSA-p293-qw3h-jr36. Use patched Next.js 15 with the same App Router/TypeScript/Tailwind architecture. React and Recharts are updated compatibly. No feature scope changes.

* Use `session_started` (Part 4) rather than the `problem_started` alias in Part 2.
* Preserve the event catalog in `event-schema.md`, followed by documented extensions before code is added. Every event belongs to constructs 1–7 or their integrity mechanisms.
* `invalidated_by` in the example DDL conflicts with append-only logging. Invalidation is exclusively a new event referencing an earlier event. PostgreSQL triggers reject UPDATE and DELETE.
* API creates lifecycle and AI events transactionally. Clients may emit attempts, reflections, and explicit skips, but cannot forge model delivery or close metadata.
* Authentication uses Clerk JWTs verified against its JWKS endpoint. An explicit development-only identity mode supports local work; production rejects this mode. An admin allowlist gates research exports. No credentials are stored in the browser.
* Clerk owns email/profile data; the local user table stores a stable Clerk subject and pseudonymous participant UUID rather than duplicating email addresses from the illustrative DDL.
* Latest user steering adds Mistral AI and Cloudflare Workers AI and explicitly authorizes seamless automatic fallback. Recovered failures stay in backend events; exhaustion is visible and retryable. Tests inject HTTP responses and never impersonate a live provider connection.
* Heuristic tier validation is a best-effort guard, not a semantic guarantee. Invalid responses are logged and withheld; another eligible provider may answer at the same requested level.
* Latest user direction replaces automatic abandonment on navigation with resumable conversations. Explicit completion still records a truthful status; navigation itself creates no closure event.
* Analysis uses one row per user for inference to avoid treating repeated sessions as independent respondents. AI-first group means majority of AI-using sessions are AI-first (ties classify true). This operationalization, behavioral proxies, and sample differences prevent claiming an exact survey replication.
* The published paper itself was not supplied. Only reference numbers explicitly quoted in the specification are included; missing table values remain unavailable.
* Effort = mean(min(pre-AI attempt characters / 500, 1), min(pre-AI attempt seconds / 300, 1)). This is an operational proxy, not a validated scale. No attempt means zero. No AI session has `is_ai_first=false`; first-action analysis excludes sessions without AI.
* Correctness is an explicit self-report about a particular prior attempt, not a model judgment. Unknown remains null. A positive unnecessary-use flag requires an adequate attempt submitted before a later AI request.
* Each delivered hint can receive at most one verification or explicit verification skip. Closure with AI requires these for every delivery and an evaluation or explicit evaluation skip after the latest delivery. Follow-up chat is available after level 3. Abandonment remains one-click and unrestricted.
* Event IDs are idempotency keys. Duplicate retries return the original event; conflicting reuse is rejected. Session row locking serializes writes. Server computes durations and chronology; clients cannot supply authoritative metrics.
* Rollups are persisted on mutation and refreshed on demand/nightly. Responses always expose refresh time. Historical rolling frequency uses only requests preceding the analyzed session's first request; user-level regression uses prior-seven-day mean exposure, reducing outcome leakage.

* Phase 1 on 2026-09-16 introduces chat-v1 for new web conversations: immediate answers, unrestricted follow-up questions, optional hints and independent attempts, and persisted mode changes. No attempt/verification/evaluation skip is fabricated to bypass old gates. Guided-v1 remains the default for legacy API clients and historical sessions.
* Research endpoints and CLI exports default to guided sessions and allow explicit chat selection. They do not silently pool protocols. Personal progress currently describes recorded activity; richer mode-aware interpretation belongs to Phase 4.
* The supplied logo is copied unchanged from others/logo.png. Home and navigation are simplified before a broader visual redesign. Workspace AI diagnostics belong in operator settings.
* The existing timeout regression used sub-100ms scheduling assumptions and could fail under Windows load. Its shared-budget assertion now uses a deterministic clock; the separate cancellation test still exercises a real async timeout.

## Phase 2: reserve fallback usage before calling providers

A separate database ledger reserves a whole fallback envelope atomically with each logical request. This provides shared admission limits across workers without changing append-only research events. Failed/unknown attempts retain conservative charges; interrupted requests keep their envelope while concurrency slots expire after 90 seconds. Provider-reported usage is recorded even for withheld/truncated answers.

Default allowances are 30 accepted requests per UTC day, six per minute, two concurrent per participant/eight globally, one million shared accounted tokens daily, and at most three actual provider attempts. They can be overridden in .env. Dollar enforcement is optional and requires an operator-supplied ceiling across every model/token type; estimates are not advertised as invoice caps. Existing keys and historical records are preserved.

Rendering uses react-markdown, remark-gfm, remark-math and rehype-katex. Raw HTML is skipped, remote images are replaced by text, KaTeX trust is disabled, and URL filtering stays enabled. Only assistant text is interpreted as Markdown. Concise/Detailed is explicit user intent and part of request idempotency.

## Phase 3: optional learning support without model calls

Practice invitations use delivered-answer streaks, not request attempts or inferred dependence. Three answers in Ask AI mode qualify; saving independent thinking or switching to Try myself resets the streak. A ten-minute cooldown plus three additional replies follows a decision, with at most two decided invitations per conversation. The invitation anchor is stable across reloads.

Yes changes mode atomically with the decision, with a domain-specific practice suggestion attached to the invitation's question. No does not gate another AI request. Reminder preferences are owner-scoped and stored separately from behavioral events. Optional decision and feedback saves stay outside the required offline event queue; a failed optional save cannot block sending another question. Local account-scoped dismissal survives reload when a practice decision cannot sync.

Helpful/Not helpful feedback is editable, including on completed chats. Feedback and practice choices do not fabricate attempts, skips, verification, correctness, or dependency scores. Guided study sessions retain their original protocol.
