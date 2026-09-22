# Chat review and usability follow-up

The supplied conversation moved from an overheating phone to `5*5`, then `5*9`, followed by a saved attempt of `45`. That attempt belonged to the latest multiplication question. The former Show an answer button literally requested the **original question**, and the server always labeled the opening phone question as the problem. Repeated hint requests could therefore revive unrelated phone advice.

## Implemented

- Help buttons send an explicit hint/answer intent. The server resolves it to the latest actual question, preserves that focus across repeated hints, and records it with the request/answer. Older generated button phrases are recognized so existing conversations can continue correctly without rewriting their records.
- Attempts after the current question are supplied as current work. When a new explicit question arrives, older attempts stay in chronological history instead of being labeled as the new question's attempt. The original question is still available as historical context.
- Prompts ask for a useful verification step when an attempt is already correct, discourage repetitive Answer/Direct answer labels, and discourage invented device procedures or unsafe battery handling. These instructions improve guidance but do not guarantee factual accuracy from every provider. The old advice about clogged smartphone cooling systems and battery handling is not verified evidence; it remains in the saved transcript rather than being silently rewritten.
- Settings now separates account, answer/practice preferences, daily allowance, privacy, help/sync, and collapsed workspace administration. The default Concise/Detailed preference is stored per account, included in data exports, and applied when a conversation is opened; existing pending requests retain their original answer length.
- Progress restores AI-first and time-before-AI graphs and adds a weekly own-attempts/AI-answers graph. Guided study also restores its verification graph. Protocols stay separate, empty measures stay empty, and exact table values remain available. These are activity measures, not intelligence or learning scores.
- Configured Clerk installations expose sign-in, create-account, account management, and sign-out. The current local installation clearly identifies its shared development account. No fake login or second password system was added.
- The question-first home layout is unchanged. No automatic AI analysis, provider probing, or extra model call is used for these features.

## Still needed for public launch

The workspace has no configured Clerk issuer/publishable/secret keys. Real sign-in cannot be activated or verified until the operator supplies those locally, configures frontend and API origins, and rebuilds/restarts. Existing development conversations are not silently transferred to a new account. Follow [operations](operations.md) for hosted two-account checks, TLS/deployment, encrypted backup scheduling/expiry, a support contact, and a deletion-response schedule.

Further optional work should be driven by use: streaming and cancellation with safe fallback, search within a conversation, accessible richer math input, and optional files/voice. These are not prerequisites for the corrected text-chat flow and are not represented as completed.

Local deployment preparation now includes public help/privacy, configurable support, error recovery pages, safe request references, hosted-build guards, Netlify configuration, platform-port/database-URL handling and separate schema/runtime permissions. See the [deployment handoff](deployment-checklist.md) for the remaining host/account steps.
