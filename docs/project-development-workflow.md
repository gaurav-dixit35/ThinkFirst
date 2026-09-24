# ThinkFirst — Complete Project Development Workflow

Prepared: 23 September 2026

## Purpose of this file

Use this document to create a workflow image showing **how the ThinkFirst project was conceived, planned, designed, developed, refined and tested, followed by the remaining steps toward deployment and project completion**.

This is the **project development lifecycle**. It is not a diagram of how a user chats with AI, how a model generates answers, or how a request travels through the application.

The stages summarize related work into a readable sequence. Development, feedback, documentation and testing occurred iteratively; this is not an exact commit-by-commit chronology.

## Project context

- **Project:** ThinkFirst.
- **Starting point:** A supplied research-based specification describing AI-first problem-solving behaviour and limitations of self-reported, single-point-in-time measurement.
- **Objective:** Build a usable platform that supports optional independent attempts and records observable interaction behaviour for longitudinal analysis.
- **Product principle:** Keep Ask AI and Try myself distinct, accessible and voluntary. Support thinking without forcing or shaming users.
- **Research principle:** Recorded activity is evidence of actions within the platform, not proof of intelligence, dependence, correctness or improved cognitive ability.
- **Evidence boundary:** The supplied specification informed development. This file does not claim that an independent literature review, a new participant study, or verification of the original paper has been completed.

## One-line development sequence

Research problem → Requirements and traceability → Scope and phased planning → System and interface design → Technical foundation → Initial research prototype → Owner feedback and refinement → Functional platform development → Authentication and privacy → Additional thinking support → Integration and debugging → Testing and validation → Documentation and deployment preparation → Hosted setup and verification → Pilot and research analysis → Final report and version handover.

**Current position:** Local development and validation are complete for the implemented feature batches. Deployment preparation exists. Hosted activation, a real pilot and final research conclusions remain pending.

## Detailed workflow: inputs, activities and outputs

### 01. Identify the research problem

**Input:** The project owner's idea and supplied research specification.

**Activities:** Identify the behaviours the project should help observe: seeking AI first, making independent attempts, requesting different levels of assistance, checking responses and returning to problems over time. Define the practical problem of supporting independent thinking while keeping AI accessible.

**Output:** A project problem statement and research-informed objectives.

**Status:** Completed at the specification level; no independent research findings are claimed.

### 02. Define requirements and research traceability

**Input:** The problem statement and specification.

**Activities:** Translate the objectives into functional requirements, event types, user actions, behavioural proxies and integrity rules. Map features to research constructs. Define explicit consent, optional assistance, accurate timestamps and honest handling of missing data.

**Output:** Requirements, a research-to-feature mapping and documented event contracts.

**Status:** Implemented and documented, with later extensions recorded separately.

### 03. Set scope and create development phases

**Input:** The requirements and product priorities.

**Activities:** Divide work into reviewable phases. Prioritize working functionality before visual polish. Establish acceptance criteria, cost controls and deferred features. Incorporate later owner decisions without treating every suggestion as an immediate requirement.

**Output:** A phased roadmap and a manageable development backlog.

**Status:** Established and updated throughout development.

### 04. Design the system, data and interface

**Input:** The roadmap and research contracts.

**Activities:** Design the frontend/backend boundary, database relationships, API contracts, event history, model-provider adapters and analytics pipeline. Plan clear interfaces and account ownership. Define error recovery and the distinction between everyday chat and guided research sessions.

**Output:** An implementation design covering application structure, data flow, user experience and research measurement.

**Technology context:** Next.js, React and TypeScript for the website; FastAPI and Python for the API; PostgreSQL for persistent data; Clerk for authentication; Python analytics libraries for research calculations. Docker supports local database and container preparation. Technologies were updated during development where needed.

**Status:** Implemented; this workflow does not require a separate architecture diagram.

### 05. Establish the technical foundation

**Input:** The system design.

**Activities:** Set up the repository, dependencies, local environments, database connection, API service and frontend. Implement schema setup, configuration handling and health checks. Keep secrets out of source control and separate development/test data from normal workspace data.

**Output:** A working local foundation connecting website, API and database.

**Status:** Implemented.

### 06. Build the initial research prototype

**Input:** The working foundation and event contracts.

**Activities:** Implement the original guided problem-solving flow, saved attempts, tiered assistance, verification/evaluation decisions, session lifecycle and event reconstruction. Add personal rollups, statistical analysis and research export capabilities.

**Output:** An initial functional research prototype that records behaviour and supports analysis of recorded data.

**Status:** Implemented. Historical guided sessions remain supported; their existence does not establish that a participant study was conducted.

### 07. Gather owner feedback and refine usability

**Input:** The prototype and the owner's experience using it.

**Activities:** Review complexity, screen content, AI access and confusing interactions. Simplify the home experience. Preserve separate Ask AI and Try myself modes, make practice voluntary, improve conversation continuity and apply the supplied logo. Correct mixed-topic help behaviour based on the owner's example conversations.

**Output:** A simpler everyday experience alongside the preserved guided protocol.

**Status:** Implemented through iterative owner feedback. Do not label this as a formal user study.

### 08. Develop the functional platform

**Input:** The refined experience and approved feature priorities.

**Activities:** Build and connect the useful application features:

- Multi-provider AI integration with bounded fallback and usage limits.
- Saved conversations, follow-ups, readable answers and independent attempts.
- Streaming, Stop generating, safe question editing and answer regeneration.
- History, search, conversation management and restored progress graphs.
- Optional practice invitations, answer feedback and on-demand conversation reviews.
- Saved answers, deliberate retries, weekly goals and related exercises.
- Answer-language preferences, exports and support-report handling.

**Output:** A usable, connected local platform.

**Status:** Implemented and locally checked. Features were delivered in batches, rather than in one uninterrupted build.

### 09. Add authentication, privacy and operational safeguards

**Input:** The platform and requirements for separate personal workspaces.

**Activities:** Integrate Clerk login/signup pages and API token verification. Enforce ownership boundaries, separate browser drafts by account, provide research consent and personal export/deletion controls, and add operator access restrictions. Prepare safe configuration, runtime database permissions and deployment checks.

**Output:** Account-aware application code, privacy controls and operational safeguards.

**Status:** Locally implemented. Real Clerk forms load; complete real-account and hosted walkthroughs remain part of Stage 14.

### 10. Add optional thinking and verification support

**Input:** The owner's request to strengthen research relevance while preserving the existing structure.

**Activities:** Add Check my thinking inside Try myself, optional verification reports beneath responses, stable question-turn references and an expandable thinking-activity view. Keep earlier metrics and protocols intact. Avoid extra AI calls for ordinary tracking and reporting.

**Output:** Additional support for independent attempts, reported verification and question-specific activity inspection.

**Status:** Implemented. AI feedback is not certified grading, and activity counts are not ability scores.

### 11. Integrate components and resolve defects

**Input:** Connected features, reported problems and observed failures.

**Activities:** Verify frontend/API contracts, question context, account configuration, request replay, provider fallback and recovery. Resolve the reported local Internal Server Error caused by the website hostname mismatch. Correct outdated test fixtures and restore database connectivity after Docker interruptions.

**Output:** Integrated features and corrected application defects, with remaining environment limitations documented.

**Status:** Application fixes completed locally. A Docker default image-store defect remains documented; isolated container checks succeeded without resetting database volumes.

### 12. Test, inspect and validate

**Input:** Completed implementation batches and fixes.

**Activities:** Run backend tests on isolated SQLite/PostgreSQL data, browser interaction checks, production builds and TypeScript validation. Check authentication boundaries, recovery, privacy, mobile layout and relevant smoke scenarios. Inspect screenshots where useful. Fix failures and rerun affected checks.

**Output:** Recorded validation evidence and known limitations.

**Latest thinking-support batch evidence:**

- Full SQLite suite: **149 passed; 3 PostgreSQL-only skips**.
- Focused PostgreSQL coverage after final refinements: **25 passed**.
- Browser scenarios: **17 passed**.
- Separate real Clerk login/signup form smoke: **1 passed**.
- Production and QA builds: passed, including TypeScript checks.
- API health: database connected and Clerk authentication mode active.

These are separate runs with different scopes; do not add them together into a unique test-case total. Routine generation tests used synthetic providers, not paid live AI calls. Earlier broader validation and container results are documented separately.

**Status:** Completed locally for the implemented batches. This does not substitute for hosted or real-participant validation.

### 13. Document the project and prepare deployment

**Input:** The working application, implementation decisions and validation evidence.

**Activities:** Maintain setup instructions, event contracts, measurement decisions, feature notes and test results. Prepare Netlify website configuration, an API Dockerfile, environment inventories, database migration/permission commands, backup/restore tooling and an operational handoff checklist.

**Output:** A documented local prototype and deployment preparation package.

**Status:** Prepared. Hosting credentials, production configuration and operating arrangements still require activation.

**Current milestone:** Implemented local prototype with completed batch validation and deployment preparation.

### 14. Configure hosting and verify the deployed system

**Input:** The deployment package plus owner-controlled accounts, domains and production settings.

**Planned activities:** Configure the selected website/API/database hosts, production Clerk instance, domains, HTTPS, exact origins and secrets. Apply production schema and restricted permissions. Set spending limits, support ownership, scheduled backups and monitoring. Verify real signup, recovery, sign-out, two-account separation and deliberately bounded live provider behaviour.

**Expected output:** A verified hosted pilot environment.

**Status:** Pending. Netlify for the website and Railway for API/PostgreSQL are the documented deployment plan, not a completed deployment.

### 15. Run a consented pilot and analyze research data

**Input:** The verified pilot environment and an agreed research protocol.

**Planned activities:** Define recruitment, consent, measures, observation periods and data-quality rules with the project supervisor. Collect longitudinal interaction records from consenting participants. Keep different protocols and measurement versions identifiable. Analyze patterns with methods appropriate to the data; use the existing statistical tooling where justified. Design a comparison study separately if testing whether a feature causes behavioural change.

**Expected output:** A documented pilot dataset, research analysis and clearly bounded findings.

**Status:** Pending. Do not invent participant numbers, effects, statistical significance or claims that ThinkFirst improves thinking.

### 16. Prepare the final report and hand over the version

**Input:** Validated software, actual deployment/pilot outcomes, documentation and known limitations.

**Planned activities:** Assemble the project report, development workflow diagram, system description, screenshots, implementation evidence, testing results and any actual research findings. Prepare the demonstration and handover instructions. Mark remaining work honestly and agree on the accepted version's completion criteria.

**Expected output:** Final project submission and an accepted version handover.

**Status:** Pending formal submission/handover. Local prototype completion and completion of a research study are different milestones.

**After handover:** Continue maintenance, monitoring, issue resolution and carefully selected improvements. A version can be finished while the platform continues to evolve.

## Feedback loops to show in the image

1. **Owner feedback:** Stage 07 → Stage 04 and Stage 08. Label: “Refine design and priorities”.
2. **Failed checks:** Stage 12 → Stage 11 → Stage 12. Label: “Fix and retest”.
3. **Pilot findings:** Stage 15 → Stage 03. Label: “Plan the next iteration”. Mark this loop as future work.

Do not represent the lifecycle as a one-pass process where testing happens only once. Small implementation batches were completed and checked throughout development.

## Exact short labels for the workflow image

Use these as the visible boxes. Keep the detailed material above as context, not text to squeeze into the diagram.

| Node | Box title | Short subtitle | Status label |
| --- | --- | --- | --- |
| 01 | Research Problem | Review the supplied specification | Completed |
| 02 | Requirements | Map features to research constructs | Completed |
| 03 | Scope and Planning | Set phases and acceptance criteria | Completed |
| 04 | System and UX Design | Plan architecture, data and interfaces | Completed |
| 05 | Technical Foundation | Connect frontend, API and database | Completed |
| 06 | Research Prototype | Implement guided flow and event logging | Completed |
| 07 | Feedback and Refinement | Simplify through owner feedback | Completed |
| 08 | Platform Development | Build and connect useful features | Completed locally |
| 09 | Accounts and Privacy | Add access and data controls | Implemented locally |
| 10 | Thinking Support | Add feedback and question tracking | Completed locally |
| 11 | Integration and Debugging | Resolve defects and recovery issues | Local fixes completed |
| 12 | Testing and Validation | Check behaviour, builds and usability | Local checks passed |
| 13 | Deployment Preparation | Document setup and operations | Prepared — current milestone |
| 14 | Hosted Verification | Deploy and verify real services | Pending |
| 15 | Pilot and Analysis | Collect consented data and analyze | Pending |
| 16 | Report and Handover | Present evidence and finish the version | Pending |

## Ready-to-use prompt for ChatGPT image generation

Copy this prompt with the file attached, or paste this entire file into ChatGPT:

> Create a clear, professional workflow infographic titled **“ThinkFirst — Project Development Lifecycle”** using the attached document as the factual source.
>
> Show the **development journey of the project**, from research problem and requirements through design, prototype, owner feedback, implementation, debugging, testing, deployment preparation, future hosted verification, pilot analysis and final handover. Do not turn this into an app navigation flow, AI response pipeline or software architecture diagram.
>
> Use the **16 numbered nodes and their short subtitles** from the “Exact short labels” table. Arrange them as a readable vertical flow or a spacious multi-row sequence with unambiguous directional arrows. Choose sufficient image size for legible text. Group related stages visually into planning, prototype/development, validation/preparation, and future release/research. Avoid crossing arrows through boxes or text.
>
> Use solid green or teal boxes for completed/local implementation stages, an amber milestone around **13 — Deployment Preparation**, and outlined grey boxes with dashed connectors for **14–16**, explicitly labelled **Pending**. Include a small legend. Status must also be readable through labels and line styles, not colour alone.
>
> At Stage 13, add a clearly visible marker: **“Current milestone: locally validated prototype; deployment preparation complete.”** Do not imply that public deployment, real-account end-to-end verification, a participant pilot or research conclusions are already complete.
>
> Show compact feedback arrows: **07 → 04/08: Refine**, **12 → 11 → 12: Fix and retest**, and a dashed future arrow **15 → 03: Next iteration**. Keep these secondary to the main sequence.
>
> Use a clean academic presentation style, an off-white background, dark readable text, consistent rounded rectangles, generous spacing and restrained icons. Keep each box to its number, title, short subtitle and short status. Use the supplied logo only if it is attached; otherwise use the project name as text. Do not invent a logo, findings, participant counts, completion dates or research results. Do not copy the long stage explanations into the image.
>
> The ending should read **“Final report and version handover — planned”**, followed by a small optional maintenance loop. The image must distinguish **what has been built** from **what is still planned**. Produce the workflow image, not an explanation of how to draw one.

## Repository basis

This lifecycle is based on the project's specification, roadmap, implementation decisions, functional-update notes, thinking-support notes, validation record and deployment handoff documentation. The stage numbering above is for this presentation and does not replace the repository's earlier development-phase numbers.
