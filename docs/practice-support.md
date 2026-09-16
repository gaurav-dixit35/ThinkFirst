# Optional practice support (Phase 3)

Practice invitations are optional learning prompts, not assessments of intelligence or dependence. They never consume AI allowance or call a model.

## Contract

- New everyday conversations become eligible after three delivered answers in Ask AI mode without a saved independent attempt. Failed requests and provider retries do not count. Switching to Try myself or saving an attempt resets the streak.
- The invitation stays anchored to the answer that crossed the threshold. Ignoring it never blocks chatting. No modal or required reflection is added.
- Yes saves a `practice_invitation_responded` event and switches to Try myself in the same transaction. The task uses the question associated with that invitation and a domain-specific practice suggestion, with no generated question or prewritten participant answer. Existing drafts are preserved.
- No saves the decision and keeps chatting. A new invitation requires at least three additional delivered answers and ten minutes after the previous decision. At most two invitations can be answered per conversation. Reloading does not reset these rules.
- `GET /preferences` and `POST /preferences` read/update the authenticated user's `practice_reminders` boolean, enabled by default. Turning reminders off applies across conversations and devices. Settings can turn them on again. Existing guided sessions do not show invitations or change their protocol.
- `GET /sessions/{id}` includes server-derived `practice` state. `practice_invitation_responded` references an eligible `answer_event_id` and a decision (`try_myself` or `continue_ai`). An already decided anchor is not recorded twice, including concurrent tabs. Decisions are separate from attempts and correctness.
- `answer_feedback` references a delivered `answer_event_id` in the same chat and a rating (`helpful`, `not_helpful`, or `cleared`). The latest event is the current rating; event-ID retries are idempotent. Feedback can be edited on completed chats, does not reopen them, and is not a correctness verification.
- Optional controls use their own requests, outside the required attempt-sync queue. A failed optional save never prevents an AI request. A local, account-scoped dismissal suppresses the same invitation if saving fails; retry is offered. No answer, attempt, or verification is fabricated.

No automatic deeper analysis, grading, gamification, or extra AI summary is included in this phase.
