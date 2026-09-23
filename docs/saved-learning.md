# Saved answers and deliberate retries

This update adds useful workspace actions rather than informational pages. The unfinished Features, About, FAQ, How it works and Feedback pages were removed before this release.

- Save a delivered response from a chat, including a completed conversation. Each answer version has its own bookmark.
- Open Saved from the workspace navigation. Search questions and answers, filter questions not yet retried, and paginate results.
- Open a saved question to retry it. The original response is initially hidden; users can save their own attempt before comparison, or reveal the earlier response directly.
- Attempts remain available for later comparison. Drafts and failed-save recovery use existing account-scoped browser storage and the event queue.
- Progress shows currently bookmarked questions retried and retry attempt counts separately from first attempts in chat. These are activity counts, not correctness or mastery claims.

There are no AI calls for these features. This saved-retry flow adds no automatic grading, notifications or background summarization. The subsequent functional completion batch adds optional related exercise generation, weekly goals and language preferences; see functional-updates.md.

## Data behaviour

`answer_saved` and `learning_attempt_submitted` use existing append-only events. They reference a delivered answer in the same owned everyday conversation. Retry attempts require an active bookmark. Event IDs prevent duplicate saves after network recovery. Completed conversations allow these new events without reopening the original conversation or altering its AI context, first-attempt metrics or review fingerprint.

Removing a bookmark hides the item but retains its events and attempts; saving that answer again restores the retry history. Existing data export includes these events. Pending conversation/account deletion blocks new writes. Operator erasure removes bookmark/retry events with their source conversation. No new schema migration or runtime table permissions are required for this update.

GET `/saved` accepts `q`, `unpractised`, `limit` (1–50), and `offset`. It returns a filtered page plus factual summary counts across current bookmarks. GET `/saved/{answer_id}` returns the owned saved question, original answer and attempts. The comparison screen hides the response visually until requested; it is not an exam or secure answer-hiding mechanism.

The initial implementation reconstructs saved state from events in the owner's bookmarked conversations. A large-scale deployment may need a materialized index; no synthetic scalability claim is made.

## Activation and validation

Restart the API and rebuild/restart the website to serve the updated code. Local Clerk activation still requires the user's credentials. No provider keys or participant records are changed by implementation.

Validation results are recorded in docs/validation.md after implementation. No tests or smoke checks ran while the feature was being built.
