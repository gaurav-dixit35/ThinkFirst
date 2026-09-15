# Implementation decisions and traceability

The master specification is preserved in `specification.md`. Phase 7 is explicitly a stretch feature and is deferred. All other local MVP phases are implemented; cloud deployment requires operator accounts and secrets.

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
* Navigation within the app explicitly closes an active session as abandoned. Browser/tab termination is not a reliable transactional boundary: sessions remain open and resumable instead of fabricating closure or losing events.
* Analysis uses one row per user for inference to avoid treating repeated sessions as independent respondents. AI-first group means majority of AI-using sessions are AI-first (ties classify true). This operationalization, behavioral proxies, and sample differences prevent claiming an exact survey replication.
* The published paper itself was not supplied. Only reference numbers explicitly quoted in the specification are included; missing table values remain unavailable.
* Effort = mean(min(pre-AI attempt characters / 500, 1), min(pre-AI attempt seconds / 300, 1)). This is an operational proxy, not a validated scale. No attempt means zero. No AI session has `is_ai_first=false`; first-action analysis excludes sessions without AI.
* Correctness is an explicit self-report about a particular prior attempt, not a model judgment. Unknown remains null. A positive unnecessary-use flag requires an adequate attempt submitted before a later AI request.
* Each delivered hint can receive at most one verification or explicit verification skip. Closure with AI requires these for every delivery and an evaluation or explicit evaluation skip after the latest delivery. Follow-up chat is available after level 3. Abandonment remains one-click and unrestricted.
* Event IDs are idempotency keys. Duplicate retries return the original event; conflicting reuse is rejected. Session row locking serializes writes. Server computes durations and chronology; clients cannot supply authoritative metrics.
* Rollups are persisted on mutation and refreshed on demand/nightly. Responses always expose refresh time. Historical rolling frequency uses only requests preceding the analyzed session's first request; user-level regression uses prior-seven-day mean exposure, reducing outcome leakage.
