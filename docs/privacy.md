# Data choices and retention

Notice version: 2026-09-16. This describes implemented behavior, not a claim of legal compliance or research ethics approval. The pilot operator must publish their identity, contact details, response times, and backup schedule before inviting participants.

## Using ThinkFirst

Questions, independent attempts, AI answers and requests, feedback, explicit skips, and server timestamps are saved to the signed-in account. Titles and preferences are editable metadata. Ordinary behavioral events remain append-only. Personal history and progress work without research consent.

Hosted users acknowledge the data notice before saving new work or requesting AI. This acknowledgment is separate from research consent. The local development identity is shared and does not represent separate people.

When a user requests AI, relevant conversation context goes to the selected service. Fallback can send that context to additional configured services. Those providers have their own retention terms; ThinkFirst does not promise that deleting a conversation erases provider-held copies. The operator must review the actual provider account settings and publish the services used before the pilot.

Drafts and pending requests are stored locally under account-specific keys. Offline events were already account-scoped. Old unscoped drafts migrate only for the original development identity. This is UI isolation, not browser-storage encryption. Anyone with access to the browser profile may inspect local data; shared devices should use separate profiles or private browsing. Signing out does not destroy unsynced work.

## Optional research

Research inclusion defaults to **off**, including for existing accounts. Opting in includes existing and future saved work. `/analytics/research` and `python -m analytics.export` select only users who are currently opted in, with chat and guided protocols kept separate. Exports can include pseudonymous account IDs, behavioral measurements, and written attempts/reflections; pseudonymous does not mean anonymous.

Turning sharing off removes the account from subsequent exports. An export already in progress or already downloaded cannot be recalled automatically. Previously saved aggregate analyses remain. Operators must restrict access to research downloads, record recipients, and handle removal requests for identifiable copies outside the application. These controls do not replace study-specific consent or ethics review.

## Export and deletion

Settings → Your data → Download my data exports only the current account: identity, saved sessions, titles, all original events including corrected/invalidated events, preferences, current privacy choices, usage accounting, and deletion requests. It excludes server credentials and other accounts. Downloads contain private text; users are responsible for files they save.

Settings → Delete my conversations requires typing `DELETE MY CONVERSATIONS`. The API records one pending request, turns off research sharing, and pauses new server writes/AI requests for that account. Reading and export remain available. The UI clearly says **requested**, not deleted. The operator sees request and account IDs under Settings → Operator support.

The operator stops all API replicas and runs the exact-ID offline command in [operations.md](operations.md). In one transaction it deletes the account's conversations, titles, events, and personal rollup, then marks the request complete. The PostgreSQL event trigger is disabled only inside this transaction under a table lock and restored before commit. A rollback restores both data and trigger state. Normal API and SQL event mutations remain blocked. Replaying a completed request never deletes later conversations.

The login identity, preferences, privacy choice, deletion audit, and usage ledger are retained. Keeping usage accounting prevents erasure from resetting today's allowance. This action does **not** delete the Clerk account. After completed erasure, reopening the workspace clears that account's old local drafts, pending requests, and event queue on that browser. Other browsers must reconnect; offline devices cannot be remotely wiped.

## Retention policy for the pilot

- Live conversation data: retained until the operator fulfills a deletion request. No automatic expiry job is implemented.
- Account and usage records: retained for account operation, allowance enforcement, and incident/accounting review. No automatic purge is claimed; the operator must choose and implement a longer-term retention period before expanding beyond a pilot.
- Research downloads: access controlled and tracked by the operator. Withdrawal applies to new exports; existing identifiable copies require manual handling.
- Backups: governed by the operator's published rotation/expiry schedule. Backups may contain erased data until they expire. Keep a restricted record of fulfilled deletion request IDs and account IDs outside the backup, and reapply erasures after restoring an older snapshot before reconnecting users or exporting research.

No deletion SLA or automatic backup expiry is promised by the app. The pilot must have a named operator who regularly reviews pending requests. Do not launch without a real contact channel and a schedule you can meet.
