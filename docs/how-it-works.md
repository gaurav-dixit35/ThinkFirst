# How ThinkFirst works

ThinkFirst lets you attempt a problem, ask AI for increasing amounts of help, and keep a record of your reasoning. It uses existing AI services; we have not trained a new model.

## Try a complete session

1. Enter a problem, such as **Solve 2x + 3 = 11**.
2. Save your own attempt, or explicitly skip it.
3. Ask for a **clarifying hint**. It should ask one question without giving the answer.
4. Check the hint against your thinking, or skip the check. Request a **partial hint** for a relevant concept or next step.
5. Check or skip, then request the **full explanation**. For this example, a correct solution subtracts 3, divides by 2, and checks that x = 4.
6. Continue with **follow-up questions** about anything unclear. Your question and prior replies stay together, even when another provider takes over. Check or skip each new reply before continuing.
7. Add or skip the final reflection and finish. Reopen the complete session in history. You can also finish independently without AI.

Responses vary because the provider generates them; the example above is not a hardcoded app response. The app never escalates hint levels automatically.

## How an answer is generated

Your browser sends one saved request ID to the Python backend. The backend checks the session, builds the prompt, and contacts a configured AI service over HTTPS. Level 1 includes the problem; level 2 adds your latest saved attempt; level 3 includes the attempt and earlier hints. Follow-up requests add your question and recent conversation. Up to 12 recent messages and 24,000 conversation characters are sent; the full timeline stays in the database.

The provider generates text from this context. ThinkFirst checks for incomplete or empty responses and applies short-hint format limits before delivering one complete response. It does not currently stream tokens. It does not browse the web, execute code, retrieve private documents, or independently prove answers correct. Your verification is a self-assessment, not an automated correctness score.

## Automatic fallback

Supported services are **Groq, Google Gemini, OpenRouter, Mistral AI, and Cloudflare Workers AI**. Legacy Claude support remains available. Groq hosts open-weight models; OpenRouter selects or routes to models; Cloudflare runs supported Workers AI models.

The backend tries `AI_PROVIDER` first, followed by the ordered names in `AI_FALLBACK_ORDER`. Each service is attempted at most once per request. Missing configurations are skipped. Timeouts, rate limits, authentication errors, provider outages, incomplete responses, and hint-format violations can trigger the next provider using the same context and requested level. Explicit provider safety refusals stop the chain. Temporarily unhealthy services receive a short cooldown; changed credentials or models get a fresh attempt.

Defaults are 9 seconds per service and 50 seconds for the provider chain. `AI_PROVIDER_TIMEOUT_SECONDS` can be set between 1 and 30, and `AI_TOTAL_TIMEOUT_SECONDS` between 5 and 55. The browser keeps waiting while recovery happens. If a network response is lost, it polls the saved request instead of generating a duplicate answer. Refreshing the page also restores a pending request. A server interruption is marked failed after 90 seconds and can then be retried.

Recovered failures do not appear as chat errors. If every eligible service fails, the app shows a final retry message; questions, attempts, and conversation remain saved. This cannot guarantee an answer during a total outage. Cooldowns are local to each API process; a multi-worker deployment would need shared cooldown storage for a global limit.

Each internal attempt records the provider, model, outcome, and latency. Only the user's request counts toward AI-use metrics. The delivered response identifies the provider that actually answered. A new reply requires a new final evaluation, so an older reflection never counts as evaluation of unseen text.

## Connect your keys

Open the root `.env` and fill available values:

```dotenv
AI_PROVIDER=groq
AI_FALLBACK_ENABLED=true
AI_FALLBACK_ORDER=groq,gemini,openrouter,mistral,cloudflare
GROQ_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
MISTRAL_API_KEY=
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_ACCOUNT_ID=
```

Cloudflare needs a Workers AI API token and account ID. A Cloudflare global API key is not a substitute. You need at least one working service; add more for fallback. Keys stay on the backend. Restart the API after changing `.env`. The session's **AI setup details** lets you choose an optional preferred provider, while automatic fallback remains controlled by the server.

Each service has a `*_MODEL` setting in `.env.example`. Model defaults are starting configurations; account access and quotas vary. A fixed OpenRouter model is preferable when a study requires repeatable model selection. Configured means credentials are present, not that they have been verified.

```powershell
# Presence check: no provider calls and no key values printed
.\.venv\Scripts\python.exe scripts/check_ai.py

# One synthetic live question, outside the research database
.\.venv\Scripts\python.exe scripts/check_ai.py --provider groq --live

# Live check using the complete configured fallback chain
.\.venv\Scripts\python.exe scripts/check_ai.py --live --fallback
```

The live checks consume normal provider usage. You can use `--provider gemini`, `openrouter`, `mistral`, or `cloudflare` to verify each individually.

## Built and remaining

Implemented: problem entry, saved attempts, three hint levels, continued chat, automatic provider fallback, request recovery, offline event queues, per-response checks, final reflections, history, personal charts, and research exports. Queued events use separate storage entries so tabs do not overwrite each other. Rejected events remain visible; unrelated sessions can still sync. Browser storage does not survive clearing site data.

Live diagnostics now confirm successful short hints from Gemini, Groq, OpenRouter, and Cloudflare. Mistral returned a rate-limit response. Groq uses `openai/gpt-oss-20b`, which was listed by the configured account; its former Llama model was unavailable. Automated provider tests still use controlled responses. These live checks establish connectivity for small prompts, not general answer quality or permanent availability. Hosted Clerk sign-in, public deployment, real participant research, and the optional adaptive-friction feature remain outside completed local validation. Functionality is the current priority; no visual redesign was made.

API references: [Gemini](https://ai.google.dev/api), [Groq](https://console.groq.com/docs/api-reference), [OpenRouter](https://openrouter.ai/docs/quickstart), [Mistral](https://docs.mistral.ai/api), [Cloudflare](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/).
