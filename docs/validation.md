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
