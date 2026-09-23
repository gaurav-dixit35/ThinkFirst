# Functional completion batch

## Implemented

- Progress includes an optional named weekly retry target (1–50 distinct saved answer versions per week). Users can change or pause the target. Counts include all topics, start Monday 00:00 UTC, and are activity counts rather than grades. Removing a bookmark does not erase that week's recorded retry; deleting its source conversation does.
- Settings supports Match my question, English, Hindi (Devanagari), and Hinglish (Latin script) for new answers, hints and reviews. Language follows every configured fallback and is included in input-budget estimates. Existing responses and cached reviews are reused unchanged. Menus are not translated.
- An open chat can create a related exercise explicitly (one AI request). The new question becomes the current help-button focus; the composer switches to Try myself. Nothing is generated in the background. Model output is not certified correct or guaranteed to omit an answer; normal AI limitations apply.
- Conversation tools export saved messages and later retries to a local Markdown file. Drafts and partial previews are excluded. Export does not call AI or send data elsewhere.
- Settings → Report a problem creates a real stored report with an idempotent ID, category, optional error reference and up to 2,000 characters. It records only user-entered content, account association and timestamps. No private conversation or logs are attached automatically. Up to 10 new reports per user per rolling 24 hours are allowed.
- Operators can page through open/resolved reports and update status in Settings → Workspace administration. Users can see their most recent 20 reports and refresh status. No email delivery or response deadline is claimed.
- New forms include labels, error/status announcements, keyboard controls and mobile-sized targets. Saved/retry controls continue to use account-scoped draft and queue recovery.

## Deployment

Two additive tables: `learning_preferences` and `support_reports`. Existing development startup creates these automatically. Before production deployment, run the owner migration and runtime grant commands again; the restricted API role must not create tables itself.

Data export schema version 2 includes learning preferences and support reports. A full conversation deletion now also erases these records and clears pending browser report state. Individual conversation erasure does not remove account-level goals/reports. The deletion screen explains the expanded full-request scope. Existing usage, account and deletion audit retention remains unchanged.

## Boundaries

Clerk activation and real hosted verification require the owner's account configuration. Hosting, domain selection, support contact, operator identity, budget and backup scheduling remain deployment tasks. Files, images, voice, classrooms, teams, payments, broad interface translation and marketing pages remain deliberately deferred.

Tests and build results are recorded in validation.md after the implementation batch is finished. No real provider calls are part of routine verification.
