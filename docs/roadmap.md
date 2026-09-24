# ThinkFirst product roadmap

The product direction approved on 2026-09-16 is: get useful help immediately, with optional independent practice. Research should support the experience rather than dictate every interaction. This roadmap supersedes mandatory hint escalation for new everyday conversations. Existing guided study sessions remain readable and keep their original protocol.

| Phase | Scope | Acceptance criteria | Status |
| --- | --- | --- | --- |
| 1 — Simple core experience | Question box on the home page; Ask AI and Try myself in one conversation; immediate answers and follow-ups; optional hints; ordinary navigation preserves work; provider setup moved out of chat; supplied logo | A user can ask a question directly, save an independent attempt, request a hint or answer, switch modes, and resume the same conversation without reflection gates. Old study sessions remain compatible. | Complete |
| 2 — Sustainable free access | Actual token/usage recording for successful and failed attempts; per-user allowance and global spend cap; request/concurrency limits; bounded fallback budgets; task-appropriate answer sizes; concise/detail control; readable Markdown/code/math and copy controls | Operators can see usage and enforce limits. Users understand their allowance and can continue independent practice when it is exhausted. No promise of unlimited free API use. | Implemented and checked locally; dollar cap needs operator configuration |
| 3 — Optional learning support | Rule-based practice invitation after repeated AI turns; Yes/No choices; per-conversation cooldown and reminder preference; useful practice step; lightweight answer feedback | No extra model call decides whether to show a nudge. Declining never blocks answers or causes repeated prompting. Accepting offers a relevant, optional attempt. | Complete |
| 4 — History and useful analysis | Search and conversation titles; accurate status labels; user summaries; mode-aware progress; on-demand deeper AI summaries; research export/protocol separation | Users can find work and understand what they tried. Counts are not described as intelligence or dependence scores. New chat behaviour is distinguishable from historical guided study data. | Complete |
| 5 — Trust and launch readiness | Hosted account verification; consent and privacy controls; retention/deletion/export policy compatible with research records; operator diagnostics; deployment, backups and recovery; support process | A small pilot can run with separate accounts, clear data choices, controlled costs, and documented recovery procedures. | Local implementation complete; hosted verification and operational launch gates pending |
| 6 — Presentation and selective expansion | Further keyboard/mobile refinement; streaming/cancellation design; logo-derived visual system; optional files/voice/retrieval only if justified | Answers are readable and interactions accessible. Streaming does not merge partial answers from different providers. Additional features solve demonstrated user needs. | Planned |

Answer readability belongs in Phase 2 because it affects basic use, while broader visual polish stays in Phase 6. Broad visual redesign, extra providers, gamification, automatic per-message AI analysis, and file/voice features are not part of Phase 1.

## Working rules

- Complete one reviewable phase at a time; update this file with actual results.
- Preserve keys and participant records. Do not create synthetic records in the main database.
- Avoid paid live diagnostics during routine development. Use only focused checks needed for changed behaviour; do not repeatedly run unrelated suites.
- Do not use an AI request for counters, mode changes, reminder scheduling, or routine statistics.
- Keep advanced research and infrastructure controls outside the everyday conversation.
- Record protocol and mode explicitly; never invent attempts, verification, consent, or skipped decisions when simplifying the UI.

## Predeployment preparation result

Local release preparation adds Netlify configuration, separated web/API environment inventories, host-assigned API ports and PostgreSQL URL normalization, operator migrations and restricted runtime grants, read-only launch checks, safe request logging/references, body-size limits, public help/privacy and error recovery pages. Existing home, chat, progress and privacy flows remain available. The [deployment handoff](deployment-checklist.md) separates completed code from hosting credentials/domains, operator policy/budget choices, backup/alert activation and real hosted verification. Those require the next deployment step; streaming and optional modalities remain Phase 6.

## Phase 1 implementation checklist

- [x] Document versioned chat/session contracts before changing them.
- [x] Add direct-answer and optional-hint behaviour for new chat sessions.
- [x] Persist mode changes and preserve legacy guided behaviour.
- [x] Replace the opening dashboard with a question-first entry point.
- [x] Build one resumable conversation with Ask AI / Try myself controls.
- [x] Move provider details to settings and use `others/logo.png` unchanged.
- [x] Update documentation and run focused, non-live verification.

## Phase 1 result

Implemented and checked locally. The question-first home uses the supplied logo; new chats support immediate answers, optional hints, mode switching, saved attempts, follow-ups, and normal navigation without abandonment. Infrastructure details are in Settings. Existing guided sessions retain their rules, and research exports separate protocols.

Verification: six new API workflow checks passed, existing affected API/provider checks passed apart from a pre-existing timing-sensitive deadline test that was corrected and rerun successfully, TypeScript and production build passed, and all ten updated browser scenarios passed against synthetic providers in the isolated QA database. No live AI calls were made. Keys and main participant records were preserved.

Phase 2 implementation is now in place; see [AI allowance and cost controls](ai-usage.md). Dollar enforcement requires operator configuration and is not a provider invoice cap. Optional reminders are implemented in Phase 3 below; public launch readiness remains Phase 5.

## Phase 2 result

Implemented database-backed allowance/rate/concurrency admission, bounded fallback reservations, successful and failed provider usage recording, optional estimated-dollar enforcement, a participant allowance indicator, operator totals, Concise/Detailed requests, and safe Markdown/code/math with copy controls. The existing .env keys were unchanged. Dollar enforcement is intentionally off until a budget and price ceiling are configured; the defaults already enforce request and token limits.

Verification: ten new accounting checks passed on SQLite and again on the isolated PostgreSQL test database, including concurrent admission. All 26 provider adapter checks passed after updating prompt assertions for the new answer-style contract. The 28 chat/routing checks and 16 existing API checks passed (one PostgreSQL-only legacy check skipped in the SQLite run). TypeScript and the production build passed. Both focused Chrome checks passed after correcting Windows clipboard newline normalization and scoping an alert selector. No live provider calls or synthetic main-database conversations were made.

Phase 3 follows below. Its invitation scheduling uses counters, not extra model calls.

## Phase 3 result

Completed optional Yes/No invitations after three delivered AI answers without independent thinking, durable per-conversation cooldowns (ten minutes plus three more answers), a maximum of two answered invitations, account-scoped reminder preferences, useful domain-based practice tied to the invitation's question, and editable answer feedback. Yes preserves drafts and changes mode atomically; No and failed optional saves never block chat. Completed conversations accept feedback without reopening. Legacy guided workflows retain their original rules.

Verification: seven new practice checks and six chat regression checks passed on SQLite; all eight practice checks passed on the isolated PostgreSQL test database, including simultaneous-tab decisions. TypeScript and the production build passed. All three focused Chrome scenarios passed; the settings scenario initially exposed delayed checkbox feedback, which was fixed and rechecked along with failed-save rollback. The updated site and API are running locally. No live AI calls were made and existing keys and participant records were preserved.

Phase 4 follows below with searchable history and optional conversation reviews.

## Phase 4 result

Completed owner-scoped, paginated history search across titles and conversation text, editable/resettable titles, accurate open/completed/unfinished labels, and a new progress page with separate chat/guided activity. Personal summaries describe saved attempts and delivered answers without cognitive scores. Every chat now has a factual overview and an optional, bounded AI review using the existing allowance and fallback controls. Reviews have durable IDs, polling recovery, unchanged-source caching, and stale-source labels; they do not alter answer metrics, trigger practice prompts, or reopen completed work.

Verification: nine Phase 4 API/accounting checks passed on SQLite and again on the isolated PostgreSQL test database. Two targeted checks passed after tightening unchanged-source caching and preserving the original question in truncated review context. All 28 existing chat/routing checks passed. TypeScript and the production build passed. Six focused Chrome checks passed, including pagination/search/rename, lost-response review recovery, pending-review polling with no new generation, protocol-separated mobile progress, and existing answer-formatting/allowance behavior. No live AI calls were made. The updated website and API are running locally; keys and existing participant records were preserved.

Next: Phase 5 — trust and launch readiness: hosted accounts, data choices, retention/export/deletion, deployment and recovery, and operator support.


## Phase 5 local implementation

Added explicit research opt-in (default off for new and existing accounts), hosted notice acknowledgment independent of consent, account-owned JSON exports, idempotent deletion requests with clear pending/completed states, and an offline exact-target erasure command. Erasure keeps account and quota records, preserves other accounts, and restores event immutability transactionally. Browser drafts and pending AI requests are account-scoped; completed erasure clears the owner's old device queue on reconnect.

Authentication now rejects unknown modes, insecure hosted origins, and invalid signed session claims. Operator diagnostics show pending deletion references without conversation text. Database errors avoid logging private SQL parameters. Containers run without root, deployment ports bind to loopback, Docker contexts exclude local secrets, and PostgreSQL backup/restore tooling uses binary-safe files and new restore databases only. See [privacy](privacy.md) and [operations](operations.md).

Remaining launch gates: real Clerk credentials and hosted URLs are absent; hosted two-account verification, deployment/TLS, scheduled encrypted backups with a published expiry period, an operator support contact/deletion response schedule, and a deliberately budgeted live provider check still require the actual pilot environment. No public deployment or automatic retention scheduler is claimed. Phase 6 visual work can follow local Phase 5, but these launch gates must close before inviting users.

Verification: 45 SQLite API/authentication/chat/history checks passed (one additional PostgreSQL-only check skipped); all five privacy checks passed on PostgreSQL. TypeScript, the production build, seven focused browser scenarios, and production Compose configuration validation passed. An isolated synthetic-data backup restored with matching counts and enforced event protection. No paid provider calls were made. See [validation details](validation.md).


## Usability follow-up after Phase 5

Reviewed the user's mixed-topic phone/arithmetic chat and corrected help-button focus and attempt association. Reorganized Settings, added account answer-length defaults and sync/help controls, restored protocol-separated progress charts, and exposed configured Clerk account/signup controls. The home layout stays unchanged. See [chat review and remaining gaps](chat-review.md). These changes implement part of Phase 6; streaming/cancellation and text-chat controls are now implemented; optional modalities remain deferred. Phase 5 hosted launch gates are still open.

## Saved answers and retries

[Saved learning](saved-learning.md) adds answer bookmarks, searchable saved work and deliberate retries with the earlier answer hidden until requested. Saving, retrying and comparison use no AI requests. Progress counts these retries separately from first attempts; it does not assign grades. Personal account activation still needs Clerk credentials. Learning goals and language preferences are included in the subsequent functional completion batch below.

## Functional completion batch

See [functional updates](functional-updates.md) for weekly goals, language preferences, related exercises, Markdown conversation export and stored support reports. Only explicitly generating an exercise uses a new AI request; the other features do not. Production needs the additive table migration and refreshed runtime grants before startup.

## Optional thinking support — first additive batch

Ask AI and Try myself keep their existing structure. [Thinking support](thinking-support.md) adds explicit attempt feedback inside Try myself, optional verification reports on responses, and collapsed per-question-turn activity. Stable anchors keep mixed-topic attempts and regenerations associated with their source question. Existing session metrics and the guided protocol remain unchanged. No new pages or schema tables are introduced. Confidence checks, delayed retries, reviewed problems and comparative research setup remain deferred.
