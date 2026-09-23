# AI allowance and cost controls

ThinkFirst can offer an owner-funded allowance. It does not make commercial AI APIs unlimited or inherently free. Provider free tiers and credits still belong to the workspace owner.

## Defaults

| Setting | Default | Meaning |
| --- | --- | --- |
| `AI_USER_DAILY_REQUESTS` | 30 | Accepted AI requests per participant per UTC day, including failed requests |
| `AI_USER_REQUESTS_PER_MINUTE` | 6 | Accepted requests in the previous 60 seconds |
| `AI_USER_CONCURRENCY` | 2 | Pending replies across a participant's conversations |
| `AI_GLOBAL_CONCURRENCY` | 8 | Pending replies across the workspace |
| `AI_GLOBAL_DAILY_TOKENS` | 1000000 | Shared accounted tokens, including pending/unknown reservations |
| `AI_MAX_PROVIDER_ATTEMPTS` | 3 | Maximum actual provider calls per request, within existing timeouts |
| `AI_GLOBAL_DAILY_BUDGET_USD` | 0 | Optional estimated-dollar budget; zero disables this cap |
| `AI_MAX_USD_PER_MILLION_TOKENS` | 0 | Operator-supplied price ceiling applied to every token type |

Set overrides in the local `.env` and restart the API. Invalid settings fail startup. Keys are unaffected. These values are not provider prices. In development, the shared local identity also shares one daily allowance; independent hosted accounts remain a launch-readiness requirement.

## How enforcement works

Before a model call, one database transaction accepts the logical request, reserves its entire fallback envelope, and persists the request event. A shared database lock serializes admission across API workers on PostgreSQL and SQLite. A retried event ID returns its existing result and does not consume another allowance. Mode switches, saving thinking, history, counters, and copying answers make no AI requests.

The reservation uses the exact bounded prompt's UTF-8 byte size, framing headroom, the largest configured output budget, and the allowed attempt count. It is deliberately conservative and can reject a long question even when the displayed request count is positive. Unconfigured and cooling services do not consume an attempt. There are no extra automatic retries of a failed logical request. Existing frontend transport retries reuse its ID.

Provider attempts record reported input, output, total, reasoning, and cached token counts when available. Reasoning is not double counted for OpenAI-compatible responses. Anthropic cache reads/writes are included in the input total. Failed, truncated, and withheld hint responses retain their reported usage. Provider refusals still stop fallback.

On completion, unused fallback reservations are released. An attempt with unknown total usage keeps its full estimated token charge, even if the failure may actually have cost nothing. An interrupted worker retains its entire reservation for that day. After 90 seconds its concurrency slot is available again; its saved logical request is never sent again. A provider can continue charging after a network timeout, which is why unknown usage is not treated as zero. Reservations and requests are attributed to their admission day in UTC, including work crossing midnight.

`GET /ai/usage` returns the authenticated participant's allowance. Only a research administrator or the local development identity receives workspace totals. Settings shows measured tokens separately from accounted tokens, which include estimates and pending reservations. Usage before this feature was installed cannot be reconstructed from old events and is not included. No background provider calls retrieve billing information.

## Dollar limits and their boundary

Enable `AI_GLOBAL_DAILY_BUDGET_USD` only with a positive `AI_MAX_USD_PER_MILLION_TOKENS` covering the most expensive input, output, reasoning, cache-write and other token charges for every configured model, including models selected by an automatic provider router. Recheck the ceiling when changing models or pricing. No price was guessed or silently added to your real `.env`.

Admission rejects requests whose full reservation would exceed the configured estimated-dollar budget. Final accounting uses the higher of the ceiling-based estimate and any provider-reported cost (currently OpenRouter). Reported overages are retained. An incorrect ceiling, provider-side continuation, non-token charges, or calls made outside this app can exceed the provider bill you intended. This is an application estimate budget, not a hard provider invoice cap. For a hard financial boundary, use the provider's own account/key spending controls as well. Dollar enforcement remains **off by default** until configured; request, concurrency, attempt, and shared token limits are active by default.

## Answers

New chat requests default to Concise; Detailed explicitly increases the output budget. Hints keep their existing content restrictions and smaller budgets. Recent history stays bounded; fallback sees the same question, saved attempt, conversation, and answer style. A truncated reply is withheld and its usage recorded before fallback.

Assistant messages render Markdown, tables, fenced code and `$...$` / `$$...$$` math. Copy answer preserves the original Markdown; Copy code copies the code text. Raw HTML is skipped, unsafe URL protocols are filtered by react-markdown, remote images do not load, and KaTeX trust is disabled. Older answers using other math delimiters may remain literal text.

Reference contracts: [react-markdown security and math integration](https://github.com/remarkjs/react-markdown), [OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting), and [Gemini token accounting](https://ai.google.dev/gemini-api/docs/generate-content/tokens).


## Streaming, cancellation and new answer versions

Direct-answer previews use the same admitted request and fallback envelope. Browser preview polling does not generate answers. Stop cancels the provider task; any incurred or unknown usage stays in the ledger. Partial previews are cleared on completion, cancellation or failure and are not delivered-answer events. A provider switch replaces the preview instead of concatenating output.

Regeneration is an explicit new AI request and uses allowance. It does not overwrite earlier answers or reuse their request ID. Editing a question creates a separate conversation with bounded earlier context; the Save edit and ask AI button uses one new request. Automatic reconnect uses the original request ID and polls saved state before resubmitting.

## Saved answers and retries

[Saved learning](saved-learning.md) adds answer bookmarks, searchable saved work and deliberate retries with the earlier answer hidden until requested. Saving, retrying and comparison use no AI requests. Progress counts these retries separately from first attempts; it does not assign grades. Personal account activation still needs Clerk credentials. Learning goals and language preferences are included in the subsequent functional completion batch below.

## Functional completion batch

See [functional updates](functional-updates.md) for weekly goals, language preferences, related exercises, Markdown conversation export and stored support reports. Only explicitly generating an exercise uses a new AI request; the other features do not. Production needs the additive table migration and refreshed runtime grants before startup.
