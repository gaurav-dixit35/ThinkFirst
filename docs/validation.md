# Validation record

## Automatic fallback and functional recovery — 2026-09-15

- **PostgreSQL 16: 68 tests passed.** Tests include all five provider request builders, response parsing, same-context fallback, timeout cancellation, the shared total deadline, rate limits, invalid credentials, malformed/empty/truncated answers, hint overshoots, cooldowns, changed credentials, safety refusal handling, all-provider failure, one-request accounting, stable retry IDs, ownership-safe result polling, follow-up continuity, and evaluation after the latest response.
- **SQLite: 67 passed, 1 skipped.** The skip is the PostgreSQL-specific row-lock concurrency test.
- **Frontend:** production compilation and TypeScript validation passed. The previous dependency-maintenance pass reported zero npm audit vulnerabilities; this pass did not change dependencies.
- **Browser: 10 scenarios passed** in local Chrome against a production build. Four new scenarios cover all hint levels plus follow-up chat under fallback, recovery when a completed HTTP response is dropped, page reload during an AI request, and concurrent offline saves across tabs with a rejected event in an unrelated session. The six existing independent/skip/provider-choice/draft/mobile/offline scenarios also passed.
- The normal API was restarted and its health/database connection and five-provider fallback configuration were checked without creating participant events.

Provider tests inject synthetic HTTP responses. They verify the actual request construction, routing, backend logging, and frontend behavior; they do not establish live provider availability or answer quality. Browser QA uses `tests/browser_api.py`, which requires the `thinkfirst_test` database and strips real keys. Port 8001 has no provider credentials; port 8002 uses synthetic provider responses. The main database was neither seeded nor cleared.

At the initial implementation check, provider-key fields were blank; the later live validation below supersedes that setup status. Missing environment variable names were added without changing existing values. Cloudflare Workers AI requires both an API token and account ID. Live tests were initially pending; subsequent results are recorded below. Use `scripts/check_ai.py --provider <name> --live` for each service or `--live --fallback` for the configured chain; these diagnostics do not write research events.

Hosted Clerk sign-in, production deployment, and a real-cohort statistical study remain unverified. The original paper's full tables were not supplied; no missing reference values are invented. Adaptive friction remains the deferred stretch feature. The API test suite reports upstream Starlette/HTTPX deprecation warnings; the tested paths pass with the locked dependencies.

## Live connection troubleshooting

The provider keys and Cloudflare account ID are now present. The running API initially held the older empty configuration. Sandboxed outbound connections also failed, while the same diagnostics succeeded with normal network access. The API must run with network access to reach provider endpoints.

Live, synthetic level-1 requests succeeded through Gemini, Groq, OpenRouter, and Cloudflare. An automatic fallback diagnostic delivered an OpenRouter response. Mistral returned HTTP 429. Groq's configured `llama-3.3-70b-versatile` was unavailable; its authenticated model list included `openai/gpt-oss-20b`, which subsequently returned a valid live hint. GPT-OSS requests now reserve completion tokens for reasoning and the visible answer, following [Groq's reasoning documentation](https://console.groq.com/docs/reasoning). Groq is the local preferred provider; other services remain in the fallback chain.

These diagnostics do not create research events. One Groq response failed the short-hint format guard and was withheld; a later request passed. This illustrates why live success is not a guarantee that every response will pass validation. Docker/PostgreSQL was also found stopped during reconnection and needed to be restarted.

The complete live API workflow then passed in a disposable SQLite database: own attempt, three hint levels, a follow-up question, explicit verification/evaluation skips, and closure. It recorded exactly four requests and four delivered responses. This test used the actual provider adapter and request routing and left the main database untouched. A live response initially invented an arithmetic mistake in a correct attempt; the full-explanation prompt now explicitly forbids inventing participant steps or errors. A subsequent live explanation correctly acknowledged the saved attempt. This is a regression example, not a guarantee of universal model correctness.

After the Groq adapter update, 48 provider/routing tests passed. A new regression covers reasoning models exhausting the completion budget before emitting a visible hint. The diagnostic CLI now prints UTF-8 on Windows so Unicode model responses do not crash the check. PostgreSQL and the local website/API were restored and their HTTP health checks passed.


## Phase 1 everyday conversations — 2026-09-16

- Six new API tests cover immediate answers without invented skips, follow-up chat, optional hints, persisted modes, protocol-aware idempotency, closed-chat restrictions, and research protocol separation.
- The affected API/provider/routing run passed 69 checks with one PostgreSQL-only skip and exposed an existing sub-100ms timing assumption in a timeout test. The test now uses a deterministic clock. The six new API tests and corrected timeout test passed together (7 passed); real cancellation remains covered separately.
- TypeScript validation and the production frontend build passed.
- All ten updated Chrome browser scenarios passed with synthetic provider responses and an isolated QA database. Coverage includes the new home/logo, direct answers, follow-ups, modes, optional hints, completion without reflection forms, dropped-response and reload recovery, drafts, offline sync, navigation preserving open sessions, mobile width, and historical guided sessions.
- No live AI calls were made. Keys and the main participant database were preserved. The normal app was restarted with the updated code; QA servers were stopped after verification.

Remaining work is in roadmap.md. Phase 1 does not include token quotas, practice nudges, rich answer rendering, or a public launch.

## Phase 2 — September 16, 2026

- Accounting: 10 focused tests passed on SQLite and on the separate thinkfirst_test PostgreSQL database. Covered request idempotency, retained failed-response usage, unknown-usage reservation, fallback attempt limits, pre-call dollar/token rejection, concurrent admission, concurrency expiry, rate limits, output preferences, and administrator visibility.
- Regression: 28 chat/routing checks passed; 26 provider adapter checks passed after their prompt assertions were updated for the explicit answer-style suffix; 16 legacy API checks passed, with one PostgreSQL-specific check skipped on SQLite.
- Frontend: TypeScript and production build passed. Two new Chrome checks passed: safe math/table/code rendering, both clipboard controls, no model-supplied script/image execution, mobile width, answer preference propagation, preserved draft after HTTP 429, and independent thinking after allowance exhaustion. Initial browser assertions were corrected for Windows CRLF clipboard normalization and Next.js's separate route-announcer alert.
- Runtime: restored the existing PostgreSQL container, started the updated production website and API, and used read-only health/configuration/allowance requests. Real API keys and main participant records were preserved. No live AI generation or billing calls were made.
- Limitations: actual provider invoices and live model output quality were not revalidated. Dollar enforcement requires explicit budget/rate-ceiling configuration and does not guarantee a provider invoice cap. Hosted identity and launch readiness remain Phase 5.

## Phase 3 — September 16, 2026

- SQLite: seven new practice checks plus six chat regression checks passed. Covered thresholds, failed-call exclusion, independent-thinking resets, ten-minute cooldown, two-decision ceiling, idempotent No, atomic Yes, preserved AI allowance, owner-scoped reminder preferences, invalid targets, legacy protocol separation, and editable feedback on closed chats without changing research verification metrics.
- PostgreSQL: eight practice checks passed against thinkfirst_test, including concurrent Yes/No submissions returning the same first decision. Synthetic provider responses only.
- Frontend: TypeScript and production build passed. Three Chrome scenarios passed: failed No save stays dismissed through reload while chat continues; Yes focuses a useful practice step and preserves/saves the existing draft without calling AI; Settings disables/restores reminders and feedback persists/clears. The Settings scenario exposed delayed controlled-checkbox feedback; optimistic state with rollback and stale-read protection fixed it. The affected scenario then passed, including a synthetic preference-save failure.
- Runtime: restarted the local production website and API, applied the additive preference table migration, and verified read-only API health/database connectivity and preference retrieval. Real keys were unchanged, no synthetic main-database conversations were created, and no live provider calls were made.

## Phase 4 — September 16, 2026

- SQLite and isolated PostgreSQL: nine Phase 4 checks passed on each. Covered text/title search, literal wildcard escaping, invalidated-text exclusion, pagination beyond 100 conversations, status/protocol/owner filters, closed-chat title edits, separated progress counts, review caching/idempotency/polling, unchanged-source reuse, changed-source generation, pre-call budget rejection, interrupted-review non-replay, real-router synthetic fallback accounting, and bounded context.
- After excluding mode-only changes from review fingerprints and retaining a bounded original question when excerpts omit it, both affected tests passed again.
- Regression: 28 chat/routing checks passed. TypeScript and production build passed.
- Chrome: all six focused checks passed. Four new scenarios verify history search/pagination/rename persistence, an explicitly requested review recovering a lost HTTP response with only one generation, pending-review polling without a POST, and protocol-separated progress/empty states on mobile. Two existing synthetic scenarios verify answer rendering/copy safety and allowance failure preserving independent work after the shared request helper was generalized.
- Runtime: the updated local API and production website were started. The migration adds conversation title metadata without rewriting historical questions. No live provider requests or synthetic main-database conversations were made; real keys were unchanged. Hosted identity and launch-readiness work remain Phase 5.


## Phase 5 validation (local, 2026-09-16)

- 20 privacy, signed-JWT and chat checks passed on isolated SQLite data. Another 25 existing API/history checks passed; one PostgreSQL-only legacy check was skipped in that SQLite run.
- All five new privacy checks passed on the isolated PostgreSQL test database, including exact-target erasure, rollback restoring event protection, other-account preservation, request replay safety, and retained usage accounting.
- TypeScript and the final production build passed. Seven focused Chrome scenarios passed across privacy and existing practice support. The initial consent check exposed delayed checkbox feedback, which was fixed with save-failure rollback. One test alert selector was narrowed to avoid matching Next.js's route announcer.
- A binary backup of synthetic `thinkfirst_test` data restored into new `thinkfirst_restore_phase5_20260916`. Six table counts matched; the restored event trigger rejected deletion; restored API health and history reads succeeded. The original database was not replaced. The ignored backup remains in `backups/phase5-test-20260916.dump`; no real participant backup was created.
- The production Compose template passed configuration validation using placeholders. Container images, TLS, and public hosting were not deployed or verified.
- The rebuilt website and updated API are running locally. Read-only checks confirmed Settings, health, database connectivity, and the privacy endpoint/no-store response. Existing .env keys and main participant conversation records were preserved. No live AI calls were made.

Still required before a pilot: production Clerk credentials/URLs and real two-account sign-in verification; container/host deployment and TLS; configured encrypted backup scheduling/expiry; a published support contact and deletion response schedule; and a deliberately bounded live provider/fallback check. See [operations](operations.md).


## Chat-context and Settings follow-up

Reproduced the supplied phone → multiplication → saved `45` sequence using synthetic replies. New API checks verify repeated hints and answers stay on `5*9`, old generated help-button phrases remain compatible, a genuinely new question does not inherit the previous current attempt, and help intent participates in request replay validation. Answer-length defaults are owner-scoped and included in personal export.

Twenty-five focused chat/context/history/practice API checks passed on isolated SQLite (one existing PostgreSQL concurrency check skipped). TypeScript and the production build passed. Twelve focused browser scenarios passed after correcting two test selectors; they cover saved answer defaults, current-question hint intent, privacy export/deletion, reminders, history/review recovery, and protocol-separated mobile progress. Visual review additionally caught a CSS max-width rule collapsing Recharts drawing areas; removing it restored the drawing width, and the chart check now asserts real drawing-area widths as well as axes/points. No provider credits were used.

The local PostgreSQL container had stopped because Docker Desktop was not running. Restarted Docker Desktop and the existing `res-db-1` container without recreating its volume; the updated API then started successfully. Read-only health, preferences, and progress endpoint checks passed. Existing keys and conversations were preserved. Real hosted Clerk sign-in is still unverified because the required configuration is absent; see [operations](operations.md).

## Predeployment preparation

- The complete backend regression run passed: 122 passed, three PostgreSQL-only cases skipped on SQLite. Seven focused deployment checks then passed on isolated PostgreSQL, including transactional runtime grants, denial of history deletion/truncation/trigger changes/DDL, URL/port handling, schema readiness, secret-free diagnostics and request references. Temporary role/grant checks rolled back; the main participant database was not used for fixtures.
- Two hosted-environment guard checks passed. The final Next.js production build/type checks passed. Fourteen focused Chrome scenarios passed across public help/privacy without account access, support error references, history/review recovery, mobile progress, practice controls and existing privacy/settings behavior. Browser responses were synthetic.
- `npm audit --omit=dev` reported zero known vulnerabilities; `pip check` found no broken installed requirements. This is a point-in-time dependency check, not a comprehensive security audit. The Python test harness reports two upstream deprecation warnings.
- The configuration-only launch checker correctly flags the current local development environment: hosted identity/origins, restricted database credentials, operator/contact/admin identity, dollar ceiling and a fixed OpenRouter model still need deployment settings. No secrets are printed and no provider request is made by that checker.
- Restarted the local API and built web server. Read-only `/health`, `/service-info`, `/help` and `/privacy` requests returned 200 and the expected response headers. Existing real `.env` keys and conversation records were preserved. No live AI calls or external deployment were made.

Complete the [deployment handoff checklist](deployment-checklist.md) with real host credentials, domains, backups/alerts and the two-account/live-provider walkthrough before public use.

### Container verification completed — 2026-09-17

After Docker Desktop disconnected during the first image build, restarted Docker and the existing PostgreSQL container without replacing its volume. The final seven deployment checks passed on isolated PostgreSQL, including the added missing-grant detection. Six checks also passed on SQLite with the PostgreSQL-specific case skipped.

Built `thinkfirst-api:predeploy` successfully from `apps/api/Dockerfile`. An isolated container with networking disabled, no real credentials and a temporary SQLite database confirmed UID 10001, no copied `.env` or configured AI credentials, startup through `apps.api.serve`, the custom `PORT=48765`, and a successful health response with a request reference. The temporary container was removed automatically. This validates the Linux API image and entrypoint; the hosted PostgreSQL/Clerk combination still requires the deployment walkthrough. The optional Docker web image was not built; the intended Netlify website has passed its local production build.

The local web/API servers are running again. Read-only health, help and privacy checks returned 200. No live model calls were made, and the original environment keys and participant records were preserved.


## Text-chat completion — September 22, 2026

The full backend suite passed: 133 passed and three PostgreSQL-only checks skipped on SQLite. Seventeen focused upgrade/deployment checks passed on isolated PostgreSQL. Coverage includes streamed text extraction for all six adapters, reasoning-delta exclusion, incomplete-stream rejection, fallback preview replacement, persisted Stop with conservative accounting, safe edit/regeneration replay, archive filtering and exact-target erasure preserving other conversations. A first-preview throttle bug found by the checks was corrected.

The production web build and TypeScript checks passed. Twelve Chrome scenarios passed across the new mobile search/archive/deletion controls, streaming preview/Stop, keyboard editing, and existing history/review/privacy flows. Real provider transport was simulated; live keys, model availability and hosted sign-in were not probed. Local PostgreSQL, API and website were started with existing environment/data preserved.

Captured and visually checked the real local Home, Progress and Settings pages at the configured `http://localhost:3000` origin. Saved full-page images to ignored `artifacts/screenshots/home.png`, `progress.png` and `settings.png`. No synthetic conversations or AI requests were added to the live workspace. The numeric loopback origin is intentionally rejected by the current API origin allowlist; use localhost in the browser.

## Saved answers and deliberate retries — 2026-09-22

Implementation was completed before running checks, as requested. `tests/test_saved_learning.py`, `tests/test_history_progress.py`, and `tests/test_privacy.py`: **18 passed** on the isolated SQLite test database. Two existing upstream deprecation warnings remain. New coverage checks owner/conversation isolation, latest-question association, regenerated answers, retry and bookmark idempotency, closed-conversation retries, unchanged original progress metrics, search/pagination, pending deletion, export, and completed erasure. Provider generation is mocked; no live AI requests or main-workspace data are involved.

TypeScript checking passed. No browser tests, smoke checks, production build, hosted account walkthrough, or live provider checks were run for this update. Restart/rebuild is required to serve the updated code. The existing Clerk-credential activation blocker remains.

## Functional completion — 2026-09-22

The feature implementation was finished before running tests. The full isolated SQLite backend run recorded **141 passed, 3 PostgreSQL-only skips**, and one failure caused by an older test asserting the analysis system prompt had no appended language preference. Updating that assertion to preserve the review prompt and require the language instruction resolved it: the affected real-routing review test plus all five new workspace tests then passed (**6 passed**). No backend implementation changed after that full run. Existing upstream deprecation warnings remain.

New backend coverage includes generated exercise focus and replay, language on every fallback, stable weekly counts, preference preservation, report ownership/idempotency/rate limits/operator access, export and erasure of the new records. Transport/provider responses are synthetic.

**Production Next.js build passed**, including TypeScript and route generation. **Six Chrome tests passed**: three existing chat upgrade tests and three functional update tests covering language/goal settings, mobile hidden-answer practice and keyboard focus, real download contents and report submissions. Browser API requests were intercepted with synthetic fixtures; no main database or live provider requests were involved. The process sandbox prevented Playwright worker spawning; the same tests ran successfully with reviewed process access. The in-app browser Node REPL tool was unavailable, so the repository's Playwright suite was used.

No paid AI calls, hosted Clerk walkthrough, production deployment, or live provider checks were performed. No separate smoke test was run. `git diff --check` passed before the final documentation update.

Local startup after validation: existing `res-db-1` was started without recreating its volume. The updated API completed development startup (including additive schema setup) on `127.0.0.1:8000`, and the production website started on `127.0.0.1:3000`. Open `http://localhost:3000` for the configured browser origin. The temporary port-3100 browser-test server was stopped. No HTTP smoke request or live generation was made during startup.

## Local Clerk server-error repair and full regression — 2026-09-23

Reproduced the reported Internal Server Error on the Clerk-enabled website. Next.js was bound to `127.0.0.1` while requests used `localhost`; Clerk middleware rewrites caused Next.js to proxy the request back into itself, ending with `ECONNRESET`. Starting the website with `--hostname localhost` restored responses. Both npm development/start scripts now use that hostname. The local database DSN and fresh-install example use `127.0.0.1` after observing stalled PostgreSQL hostname connections. Existing credentials and main conversation records were preserved.

- Complete SQLite backend suite: **142 passed, 3 PostgreSQL-only skips**. Two upstream deprecation warnings remain.
- Complete synthetic Chrome suite: **32 passed**, with the real Clerk scenario intentionally skipped in this run. Updated older strict Settings/Progress fixtures for language, saved activity and learning-goal endpoints; the Gemini fallback transport fixture now emits SSE for streaming requests. Recovery tests verify lost responses and refresh do not issue duplicate generations.
- Separate real Clerk smoke: **1 passed** against the rebuilt normal website. Home, login, signup, help, privacy and settings returned 200; actual Clerk login/signup forms loaded, mobile width fit, and the signup screenshot was visually inspected. Adjusted the auth footer layout. No account was created or signed in by automation.
- Production and separate QA builds passed, including TypeScript and static route generation. Standalone TypeScript validation and **2 hosted-environment guard tests** also passed. `npm audit --omit=dev` reported **0 vulnerabilities**; `pip check` found no broken requirements.
- Read-only API checks returned healthy database/Clerk mode, 401 for an unsigned account request, allowed CORS for `http://localhost:3000`, and rejected an unapproved origin.

Synthetic QA now has a separate `.next-qa` build on port 3100 and dedicated API helpers on 8001/8002. Real `.env.local` and the Clerk-enabled `.next` build remain intact. Test generation uses synthetic transport responses, never paid AI providers or the main participant database. Real signup, verification/recovery, two-account hosted isolation, live model credits/output, and public deployment remain external walkthroughs.
