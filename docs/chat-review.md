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

The text-chat follow-up is now implemented: progressive answers, Stop generating, question edits in separate conversations, latest-answer regeneration, conversation search, archive/restore and individual deletion requests. Files, images, voice and richer math input remain optional later work.

Local deployment preparation now includes public help/privacy, configurable support, error recovery pages, safe request references, hosted-build guards, Netlify configuration, platform-port/database-URL handling and separate schema/runtime permissions. See the [deployment handoff](deployment-checklist.md) for the remaining host/account steps.


## Text-chat update — September 22, 2026

- Direct answers use provider streaming with saved previews, refreshed by the browser every 700 ms. Hints stay buffered until their level checks pass. The final answer is saved only after successful completion. Fallback replaces a failed provider preview instead of combining two answers; no extra AI request is used to update the screen.
- Stop generating persists cancellation and interrupts the active provider task. Incurred or unknown provider usage remains accounted for. A completed answer wins a simultaneous Stop; cancelled requests cannot deliver a later partial as a completed answer. Lost browser connections retain the original request ID for recovery.
- Edit question opens a new conversation with bounded earlier context and leaves the original unchanged. The button explicitly asks AI in that new conversation. Regeneration preserves earlier versions and is offered for the latest answer when no newer question/attempt exists.
- Conversation tools include text search with match navigation, archive/restore and an individually confirmed deletion request. Deletion is explicitly pending until the operator runs the existing offline erasure command with the request/account IDs; it is not an instant-delete claim. Other conversations and quota records remain. Edited copies are separate conversations.
- Added visible keyboard focus, Skip to content, Escape in the editor/search, Ctrl/Cmd+Enter for sending, reduced-motion behavior and larger mobile controls. Home retains its existing layout.

The actual local website is running for screenshots. The saved image files are under `artifacts/screenshots/`; they are excluded from Git because they may contain private workspace information. Hosted login and a deliberate live provider check still require deployment configuration. No paid AI calls were used for verification.
