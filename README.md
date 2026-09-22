# ThinkFirst

An AI conversation workspace with optional independent thinking. Ask for an answer immediately, switch to your own attempt, and keep everything in one saved conversation. Historical guided research sessions remain supported.

**Build plan:** [Phased product roadmap](docs/roadmap.md). **Usage guide:** [How ThinkFirst works](docs/how-it-works.md). Phase 1 introduces a question-first home page, Ask AI / Try myself modes, and optional hints without mandatory reflection forms. API keys remain a server configuration requirement.

## Local launch

Prerequisites: Python 3.11+, Node 22+, Docker Desktop running. PostgreSQL uses **55432** on the host so an existing database on 5432 can coexist.

```powershell
Copy-Item .env.example .env
docker compose up -d db
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps/api/requirements.lock.txt
.\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

In a second terminal:

```powershell
cd apps/web
npm ci
npm run dev
```

Open **http://localhost:3000**. API documentation: **http://localhost:8000/docs**.

The `.env` enables a labeled local participant. Add any available keys for **Groq, Gemini, OpenRouter, Mistral AI, and Cloudflare Workers AI**, then restart the API. Keep existing `.env` values when updating an installation. Cloudflare needs both `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; the other names are `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, and `MISTRAL_API_KEY`.

Automatic fallback is on. The preferred `AI_PROVIDER` is tried first, followed by `AI_FALLBACK_ORDER=groq,gemini,openrouter,mistral,cloudflare`, without duplicate calls to the same provider in one chain. Missing configurations and temporarily unhealthy services are skipped. Defaults allow 9 seconds per provider and 50 seconds overall; both are configurable within backend bounds. Recovered provider failures stay in the research log and do not interrupt the conversation. If every service fails, the app shows a retryable final error and keeps your work. No answer is fabricated. See [setup and explanation](docs/how-it-works.md).

Alternatively run `docker compose up -d --build` for both API and PostgreSQL; run the web app separately. Do not start both the host API and Docker API on the same port.

## Included

* Question-first home page, direct answers, free-form follow-up chat, optional own attempts and hints, persistent mode selection, resumable conversations, supplied logo, history, settings, and personal charts. Older guided sessions retain their original hint and reflection workflow.
* Strict event payload validation, server timestamps, ownership enforcement, transactional lifecycle events, serialized session writes, stable retry IDs, and PostgreSQL UPDATE/DELETE protection for raw events.
* Central `emitEvent()` with per-event, per-participant localStorage entries, cross-tab synchronization, reconnect flushing, bounded retries, and visible errors. AI and closure operations flush queued events before proceeding.
* Clerk JWT authentication integration; server-side issuer, expiration, signature and authorized-party verification; admin research allowlist.
* Persisted user rollup table, refreshed on writes, at most five-minute read staleness, and explicit refresh timestamp. The export job refreshes all participant rollups.
* Session reconstruction, per-user aggregation, Spearman coefficients, two-sided Mann–Whitney U with signed rank-biserial effects, and logistic odds ratios with 95% confidence intervals.
* JSON/CSV exports, comparison script, PostgreSQL integration tests, browser tests, and GitHub Actions.

Next.js **15.5.25** replaces the requested 14 baseline because current security advisories affect 14. The App Router/TypeScript/Tailwind architecture is preserved. React 19 and Recharts 3 are used; PostCSS is overridden to its patched release. Dependency versions are locked.

## Authentication and production configuration

Create a Clerk application. Set `AUTH_MODE=clerk`, `ENVIRONMENT=production`, `CLERK_ISSUER=https://<your-clerk-domain>`, and `WEB_ORIGINS=https://<your-web-host>` in the API environment. Set `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, and `NEXT_PUBLIC_API_URL` in `apps/web/.env.local` or the web host environment, then rebuild. Clerk handles sign-in and signup through its modal.

`ADMIN_SUBJECTS` is a comma-separated allowlist of Clerk subject IDs. The local development subject is `local-development-participant`; allowlisting it is useful only for local research previews. API access checks are authoritative even if a client bypasses a screen.

The recommended deployment is Netlify for the website and Railway for the API/PostgreSQL, with Clerk for sign-in. Start with the [deployment handoff checklist](docs/deployment-checklist.md) and separate environment inventories in `deploy/`. Root `netlify.toml` configures the website build. The API Docker image reads the host-provided `PORT`; use `/health` for readiness. Prepare schema and runtime grants separately using `python -m apps.api.migrate` and `python -m apps.api.permissions` with the owner connection. Production uses a restricted database login and `AUTO_MIGRATE=false`; only development creates tables on startup. Run `python -m apps.api.deployment --database` for read-only launch checks. Hosted credentials and live behavior still need verification during deployment.

Live provider checks have succeeded locally; see the validation record for provider-specific results. Cloud deployment and hosted Clerk sign-in remain unverified. Phase 7 adaptive friction remains an explicitly deferred stretch goal.

## Research exports

```powershell
.\.venv\Scripts\python.exe -m analytics.export --output exports
```

Produces `participants.csv`, `sessions.csv`, `reflections.csv`, `analysis.json`, and `comparison.md`, and persists a research export. Schedule this command nightly using your deployment scheduler. `GET /analytics/research` is admin-only and accepts optional ISO `start`/`end` filters, `format=csv`, and `experience=guided|chat`. It defaults to guided sessions, keeping the protocols separate. The export CLI likewise defaults to guided; use `--experience chat` explicitly for everyday conversations. `/research` provides an admin analysis screen and JSON download.

Research inference uses one row per user, with closed sessions aggregated before tests. At least 20 participants, both outcome classes, predictor variation, and a stable fit are required for logistic output. Missing/constant data yields explicit unavailable statuses. Correctness must be self-reported against a particular attempt; unknown correctness stays null.

The original paper was not attached. Only reference numbers quoted in the specification are included. Behavioral scales differ from Likert survey scales; the output does **not** claim an exact replication or causal effect. See [metric decisions](docs/decisions.md).

## Validation

```powershell
# Fast isolated SQLite checks
.\.venv\Scripts\python.exe -m pytest -q

# PostgreSQL integration (dedicated database)
docker compose exec -T db createdb -U thinkfirst thinkfirst_test
$env:TEST_DATABASE_URL='postgresql+psycopg://thinkfirst:thinkfirst@localhost:55432/thinkfirst_test'
.\.venv\Scripts\python.exe -m pytest -q

cd apps/web
npm run build
npm audit
```

For browser tests, use the isolated QA API entry point. It strips provider keys and refuses any database other than `thinkfirst_test`. Start each command in its own terminal (with the web production server on 3000):

```powershell
$env:DATABASE_URL='postgresql+psycopg://thinkfirst:thinkfirst@localhost:55432/thinkfirst_test'
.\.venv\Scripts\python.exe -m uvicorn tests.browser_api:app --port 8001
```

```powershell
$env:DATABASE_URL='postgresql+psycopg://thinkfirst:thinkfirst@localhost:55432/thinkfirst_test'
$env:QA_MOCK_AI='true'
.\.venv\Scripts\python.exe -m uvicorn tests.browser_api:app --port 8002
```

Then run `npx playwright test` from `apps/web`. Chrome must be installed. Port 8001 tests missing configuration; port 8002 injects synthetic HTTP provider responses to test fallback through the real backend and database. Neither seeds the main database or calls paid AI services. Screenshots show QA data. See [validation notes](docs/validation.md) for completed checks and remaining limits.

## Contracts and limitations

Read [the preserved specification](docs/specification.md), [event contract](docs/event-schema.md), and [implementation decisions](docs/decisions.md) before adding features. All features map to traceability rows 1–10. The append-only correction mechanism is documented before its implementation.

Ordinary browser and in-app navigation leaves conversations open and resumable. Completing a conversation is optional. Historical guided sessions keep their original reflection requirements when explicitly completed. A queued event rejected by the server remains visible and blocks actions in its own session until resolved; unrelated sessions can continue syncing; it is never silently dropped. LocalStorage does not survive browser data clearing. Tier heuristics reduce over-sharing but cannot prove semantic correctness. Before a real participant study, establish the study protocol and validate the behavioral proxies against the paper.

Integration references: [Gemini API](https://ai.google.dev/api), [Groq API](https://console.groq.com/docs/api-reference), [OpenRouter API](https://openrouter.ai/docs/quickstart), [Mistral API](https://docs.mistral.ai/api), [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/), [Clerk useAuth](https://clerk.com/docs/nextjs/reference/hooks/use-auth), and [ClerkProvider](https://clerk.com/docs/reference/components/clerk-provider). Legacy Claude support remains available.


## AI allowance and answer formatting

Phase 2 adds shared usage accounting, per-person daily and rate limits, concurrency limits, a maximum of three provider attempts, Concise/Detailed answers, and Markdown/code/math with copy controls. Independent thinking remains available when AI allowance is exhausted. Settings shows workspace usage for local development or administrators.

Defaults work without changing existing keys. The optional estimated-dollar cap needs explicit price-ceiling configuration; it is off by default and does not replace provider billing controls. See [AI usage configuration](docs/ai-usage.md) and the [implementation phases](docs/roadmap.md).

## Optional practice support

Phase 3 adds gentle Yes/No practice invitations after repeated AI answers, a saved reminder preference in Settings, a cooldown, and editable Helpful/Not helpful answer feedback. Accepting opens a relevant practice step while preserving your draft; declining leaves chat available. None of these controls call an AI provider. See [practice support](docs/practice-support.md).

## History and progress

Phase 4 adds searchable, paginated history; editable conversation titles; clear completion labels; and a progress page that separates everyday chats from guided study data. Each chat has a factual activity summary and an optional AI review with saved results, source-change detection, and the existing usage limits. Search, titles, progress and opening saved reviews do not call a model. See [history and progress](docs/history-progress.md).


## Privacy and pilot operations

Phase 5 adds optional research sharing (off by default), a hosted data notice, personal JSON exports, explicit conversation-deletion requests, account-scoped browser drafts, stricter signed-session checks, and operator support. Normal events remain append-only; authorized deletion runs through a separate offline maintenance command.

See [data choices and retention](docs/privacy.md) and [deployment, backups, recovery, and support](docs/operations.md). Local checks do not verify a real hosted Clerk account or launch the site. Configure production Clerk/URLs, publish a support and retention policy, and complete the hosted walkthrough before inviting pilot users.


Settings now groups account controls, saved answer-length defaults, practice reminders, allowance, privacy, and connection help. Progress charts are restored with separate chat and guided-study views. Hint/answer buttons follow the latest question after a topic change. See [the chat review](docs/chat-review.md) for the diagnosed issue, implemented changes, and remaining launch requirements.
