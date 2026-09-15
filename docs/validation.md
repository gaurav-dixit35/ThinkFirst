# Validation record

## Automatic fallback and functional recovery — 2026-09-15

- **PostgreSQL 16: 68 tests passed.** Tests include all five provider request builders, response parsing, same-context fallback, timeout cancellation, the shared total deadline, rate limits, invalid credentials, malformed/empty/truncated answers, hint overshoots, cooldowns, changed credentials, safety refusal handling, all-provider failure, one-request accounting, stable retry IDs, ownership-safe result polling, follow-up continuity, and evaluation after the latest response.
- **SQLite: 67 passed, 1 skipped.** The skip is the PostgreSQL-specific row-lock concurrency test.
- **Frontend:** production compilation and TypeScript validation passed. The previous dependency-maintenance pass reported zero npm audit vulnerabilities; this pass did not change dependencies.
- **Browser: 10 scenarios passed** in local Chrome against a production build. Four new scenarios cover all hint levels plus follow-up chat under fallback, recovery when a completed HTTP response is dropped, page reload during an AI request, and concurrent offline saves across tabs with a rejected event in an unrelated session. The six existing independent/skip/provider-choice/draft/mobile/offline scenarios also passed.
- The normal API was restarted and its health/database connection and five-provider fallback configuration were checked without creating participant events.

Provider tests inject synthetic HTTP responses. They verify the actual request construction, routing, backend logging, and frontend behavior; they do not establish live provider availability or answer quality. Browser QA uses `tests/browser_api.py`, which requires the `thinkfirst_test` database and strips real keys. Port 8001 has no provider credentials; port 8002 uses synthetic provider responses. The main database was neither seeded nor cleared.

The local `.env` still had blank provider-key fields at the last presence check. Missing environment variable names were added without changing existing values. Cloudflare Workers AI requires both an API token and account ID. Live tests remain pending after these are configured. Use `scripts/check_ai.py --provider <name> --live` for each service or `--live --fallback` for the configured chain; these diagnostics do not write research events.

Hosted Clerk sign-in, production deployment, and a real-cohort statistical study remain unverified. The original paper's full tables were not supplied; no missing reference values are invented. Adaptive friction remains the deferred stretch feature. The API test suite reports upstream Starlette/HTTPX deprecation warnings; the tested paths pass with the locked dependencies.
