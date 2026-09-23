# Pilot deployment and recovery

Phase 5 provides local controls and deployment tooling. Production Clerk credentials and hosted URLs are not configured in the current workspace. A real two-account hosted walkthrough, container deployment, TLS setup, and scheduled encrypted backups remain launch gates.

Use the [deployment handoff checklist](deployment-checklist.md) for the Netlify + Railway setup, separate secret inventories, migration/runtime roles and launch order.

## Local startup troubleshooting

Local Clerk login/signup screens were verified on September 23, 2026. Use `npm run dev` or `npm run start` in `apps/web` and browse `http://localhost:3000`. The scripts bind the website to the same hostname. Manually binding Next.js to `127.0.0.1` while visiting `localhost` caused a Clerk middleware rewrite to proxy back into the website and return Internal Server Error. Restart with the npm script after rebuilding if using production output.

Keep the API on `127.0.0.1:8000` and use `127.0.0.1:55432` for the local Docker PostgreSQL connection. This avoids the local database hostname connection stall observed during validation. `/health` should return database connected and `auth_mode: clerk`; an unauthenticated `/me` returning 401 is expected. Run synthetic browser checks on the separate QA website as described in [README](../README.md#validation), preserving the real Clerk build and keys.

## Configure the hosted environment

1. Use a separate PostgreSQL 16 production database and a production Clerk instance. Do not reuse the shared development database/identity. Make a restore-verified backup before every deployment that changes data structures.
2. Create an ignored `.env.production` from `.env.example` for Compose, or use the separate `deploy/api.env.example` and `deploy/web.env.example` inventories for Railway/Netlify. Set `ENVIRONMENT=production`, `AUTH_MODE=clerk`, `AUTO_MIGRATE=false`, the restricted runtime `DATABASE_URL`, `CLERK_ISSUER`, web `CLERK_SECRET_KEY`/`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `WEB_ORIGINS` (exact HTTPS website origin), and `NEXT_PUBLIC_API_URL` (HTTPS API origin). Set `CLERK_AUDIENCE` only if the Clerk session token actually contains that audience. Set `ADMIN_SUBJECTS` to the operator's Clerk user subject and publish `OPERATOR_NAME`/`SUPPORT_EMAIL`. Keep all secret keys server-side; the publishable key is intentionally public.
3. Configure the website domain in Clerk. The API verifies the RS256 signature, issuer, expiry, not-before time, subject/session claims, and exact authorized party. Unknown auth modes and insecure production origins fail startup. Short-lived signed tokens are verified locally; immediate server-side session revocation checks are not implemented. Follow [Clerk's session token verification guidance](https://clerk.com/docs/guides/sessions/manual-jwt-verification).
4. Set provider keys and price ceilings appropriate to the selected models. [AI usage controls](ai-usage.md) apply across fallback attempts. The optional dollar cap is an estimate, not an invoice guarantee; configure provider-side budgets too. No extra AI call is needed for diagnostics, counters, privacy, or progress.
5. On a Docker host: `docker compose --env-file .env.production -f deploy/compose.yaml up -d --build`. The API and website bind only to loopback ports 8000 and 3000. Serve each through a TLS reverse proxy on the configured origins. PostgreSQL is external to this production template; restrict access, configure TLS where appropriate, and supply its actual connection string. Do not use the development compose password in production.
6. Both application containers run without root. The API health check checks database connectivity. The Docker website uses Next.js standalone output; public URL/key values are embedded at build time, so rebuild when they change. Secrets are not Docker build arguments. Before startup, run `python -m apps.api.migrate` and `python -m apps.api.permissions` with the separate owner connection as described in the handoff. Production startup verifies schema/event protection and rejects privileged runtime accounts. Only development automatically bootstraps tables. Keep migration/erasure owner credentials outside the running service.

## Required hosted walkthrough

Before inviting anyone, sign in using two real accounts in separate browser profiles. Acknowledge the data notice with research sharing off. Save a different conversation in each account. Verify history, direct session URLs, AI request/review polling, export, progress, and browser drafts do not cross accounts. Test invalid/expired tokens and a disallowed origin. Verify one configured AI answer and a controlled provider fallback within a deliberately small budget, then check accounting. Local checks use synthetic providers and cannot confirm actual credits/key validity.

Confirm the operator can review requests and research exports, while an ordinary user cannot. Confirm opt-in includes a participant, withdrawal excludes future exports, and no research consent is required for ordinary chat. Use a disposable pilot account to rehearse deletion and recovery. Publish a support contact, provider/data notice, request response time, and backup retention schedule. Do not use real participant text for smoke tests.

## Backups and isolated restore drills

Use PostgreSQL 16 client tools for this PostgreSQL 16 project; see the official [pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html) and [pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html) references. `DATABASE_URL` is read from the environment or local `.env`; native tools receive credentials through environment variables, not command arguments.

```powershell
# Local Docker database. This creates a new file; it never overwrites one.
.venv/Scripts/python.exe -m apps.api.backup backup --container res-db-1 --file backups/thinkfirst-YYYYMMDD.dump

# Restores into a NEW database, never the live source or an existing database.
.venv/Scripts/python.exe -m apps.api.backup restore-drill --container res-db-1 --file backups/thinkfirst-YYYYMMDD.dump --database thinkfirst_restore_YYYYMMDD
```

For a managed database, omit `--container` and install matching `pg_dump`, `pg_restore`, and `createdb` executables. Supply the managed connection's SSL settings through `DATABASE_URL` or PostgreSQL environment variables. Docker mode is for the local container's socket authentication. The dump is binary-safe on Windows. A failed dump may leave a partial file; never treat it as a successful backup. A failed restore leaves only the new isolated target; investigate before explicitly removing it.

Encrypt backups at rest using your infrastructure's key management and restrict downloads. Schedule backups and verify age/size and restore success. The script does not schedule, encrypt, rotate, or upload files. Agree on recovery point/time objectives; measure them in a real deployment instead of inventing a guarantee.

After restoring to the isolated target, compare user/session/event counts with the source snapshot, confirm the `immutable_events` trigger is enabled, and exercise read-only `/health`, history and owner isolation against the restored database using an isolated API with provider keys unset. Keep it inaccessible to participants. Never point production at an unverified restore.

For real recovery: stop every API instance, preserve the failed database for diagnosis, restore into a new database, reapply completed erasures from the separately retained deletion register, validate, then update `DATABASE_URL` and restart. Snapshot restores can resurrect old consent; use the latest privacy-choice register where available, otherwise set research sharing off for all restored accounts until they explicitly opt in again. Retain the old database until the recovery is accepted. Public API/web URLs and Clerk identity mapping must stay consistent.

## Fulfill a deletion request

Read pending request IDs/account IDs in Settings → Operator support (`GET /operator/status`, admin-only when hosted). Schedule downtime, stop **all** API replicas, and wait for in-flight requests to end. Record the authorized request in the restricted deletion register. Then, using the database-owner role and exact IDs:

```powershell
.venv/Scripts/python.exe -m apps.api.erase --request-id REQUEST_UUID --user-id ACCOUNT_UUID --api-stopped
```

The command refuses mismatched IDs and recent pending AI requests. It preserves other accounts and quota records. It does not infer authorization from an arbitrary account ID: a matching user-originated request must exist. The `--api-stopped` flag is an operator attestation, not an automatic distributed shutdown. Restart the API, confirm the request shows completed, and ask the user to reopen the workspace. Track external research copies and backup expiry separately as described in [privacy.md](privacy.md).

For recovery of a snapshot predating a deletion request, recreate the externally recorded request with the original ID/account under controlled maintenance, then run the same targeted erasure; do not resume service first. Keep that register restricted because it contains account identifiers. Restoring old snapshots without this reconciliation is not a completed privacy-safe recovery.

## Operator support

Check `/health` for API/database availability, Settings → AI setup for configured providers and allowance accounting, and Operator support for pending deletions. These checks do not spend AI tokens. `GET /ai/status` exposes configuration names/readiness, never keys; configuration does not prove credits or connectivity.

Ask users for the conversation/request reference, approximate time, and visible error, not their API key or full private conversation. On an interrupted answer, reopen/poll the saved request before retrying a new one. On 429, review the allowance and reset time. On 503, check database/network health. On sign-in errors, check issuer, exact origins, key configuration, and token expiry. Database errors log only the exception class, not SQL parameters containing private text. Configure proxy logging to omit authorization headers, bodies, and sensitive URL query values (history searches contain user text).

Rotate compromised provider/Clerk/database credentials through the owning service and deployment secret store, then restart the affected service. Keep incident notes without private prompts. Monitor database size, backup freshness, failed provider attempts, quota denials, uptime, and pending deletion age. This repository does not provide alert delivery or an on-call service; assign a named pilot operator and an actual contact channel before launch.


## Text-chat update schema and individual erasure

Before deploying this update, run the owner migration and runtime grant commands again. Three new tables hold archive flags, individual deletion requests and response preview state (including the conversation deletion audit); the migration adds them without changing existing conversation records. The running API still uses the restricted role.

Operator status now distinguishes all-conversation requests from one-conversation requests. Use the same `python -m apps.api.erase --request-id ... --user-id ... --api-stopped` workflow for either kind after stopping all API replicas. The command resolves the exact request and removes only its approved scope, including preview/archive metadata. Other conversations, edited copies, account records and quota accounting remain. Refresh the browser after erasure so completed session IDs clear the corresponding local drafts and queued events.

## Dedicated account pages

The website now provides `/login` and `/signup`. Follow [account setup](login-setup.md) to connect a local Clerk instance without copying unrelated API secrets into the website. Real credentials and account verification remain required before launch.

## Functional completion batch

See [functional updates](functional-updates.md) for weekly goals, language preferences, related exercises, Markdown conversation export and stored support reports. Only explicitly generating an exercise uses a new AI request; the other features do not. Production needs the additive table migration and refreshed runtime grants before startup.
