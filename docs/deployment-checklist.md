# Deployment handoff: Netlify + Railway + Clerk

The local predeployment work is implemented. Nothing has been deployed or provisioned by these changes. Hosting credentials, domains, operating budget and operator contact must be supplied during the deployment step. Local checks cannot prove hosted account isolation or live provider availability.

## Included in the repository

- `netlify.toml`: web base directory, Next.js build and Node 22. Hosted builds reject missing authentication and an insecure/malformed API URL. Production Netlify builds require a live Clerk publishable key.
- `apps/api/Dockerfile`: non-root API, platform `PORT` handling and database health check. Railway PostgreSQL URLs with `postgres://` or `postgresql://` are accepted.
- Separate migration and permission commands. Production verifies the existing schema and restricted runtime role; it never creates tables or recreates event protection during startup.
- `deploy/api.env.example` and `deploy/web.env.example`: separate secret inventories. The real `.env` remains local and unchanged.
- Public `/help` and `/privacy`, configurable operator contact, error/retry pages, safe request references, request-size limits and response headers. The home/chat layout is unchanged.
- No-provider-call configuration checks: `python -m apps.api.deployment`, optionally `--database` for connectivity/schema/permissions.

## 1. Prepare accounts and domains

Create the Railway API and PostgreSQL services, Netlify website, and production Clerk instance when you are ready to deploy. Use a separate database; do not import the shared development account automatically. Choose the final website/API HTTPS origins, configure the website domain in Clerk, and copy values into each host's secret store using its matching example file. Only public API URL and public Clerk key belong in `NEXT_PUBLIC_*` variables.

For Netlify, import the repository and use the root `netlify.toml`. Do not use a static export, wildcard SPA redirect or `THINKFIRST_STANDALONE`. Scope the Clerk secret to server runtime/build as required by the Next.js middleware; never expose it publicly. Preview sites need their own approved exact origins and isolated staging credentials/data, or keep previews disabled.

For Railway API, use repository root as the build context and `RAILWAY_DOCKERFILE_PATH=apps/api/Dockerfile`. The image starts `python -m apps.api.serve` and reads Railway's `PORT`. Set the service health-check path to `/health`, timeout to 120 seconds, and restart policy to On Failure. Keep service sleeping disabled for an always-available chat experience. Enable deployment rollback and connect only the runtime database login below. Do not add the owner's database URL to the running API service.

The Railway dashboard settings are deliberate: its current documentation deprecates new `railway.toml`/`railway.json` configuration in favor of infrastructure as code. No legacy manifest is supplied. See [Railway configuration](https://docs.railway.com/config-as-code), [Dockerfile selection](https://docs.railway.com/builds/dockerfiles), and [health checks](https://docs.railway.com/deployments/healthchecks). Netlify's [monorepo guide](https://docs.netlify.com/build/configure-builds/monorepos/) explains the base/publish settings.

## 2. Prepare the database once, before starting the API

Use PostgreSQL 16 and an operator-only connection with schema ownership. For an existing database, take and verify a backup first. These commands are run from repository root in a temporary operator environment; set credentials through environment/secret tooling, not command-line arguments or checked-in files.

1. Set `DATABASE_URL` to the **owner** connection and run `python -m apps.api.migrate`. The command is transactional and serialized on PostgreSQL. It adds missing tables and verifies expected columns/event protection. It does not invent migrations for future column changes; such changes need an explicit reviewed migration.
2. In the database administrator's SQL console, create a separate role:

   ```sql
   CREATE ROLE thinkfirst_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
     NOINHERIT NOREPLICATION NOBYPASSRLS;
   ```

   Set a strong password using the administrator's secret workflow, or interactive `\password thinkfirst_runtime` in psql. Do not paste a real password into a committed SQL file or this guide. Do not grant owner-role membership or schema CREATE access. Use the dedicated database's `public` schema.
3. Keep the owner connection only in that operator process, set `RUNTIME_DATABASE_ROLE=thinkfirst_runtime`, and run `python -m apps.api.permissions`. Re-run after a release that adds tables. This grants application reads/inserts/updates; event history has only reads/inserts. No runtime DELETE, TRUNCATE or schema ownership is required.
4. Set Railway's API `DATABASE_URL` to the **runtime** connection, `AUTO_MIGRATE=false`, `AUTH_MODE=clerk`, `ENVIRONMENT=production`. Remove the owner connection from the temporary process when finished. Backups, migrations and approved erasure remain offline operator tasks.
5. Run `python -m apps.api.deployment --database` in the runtime environment. It reports only action names, not secrets. Missing keys, contact, allowance ceilings or owner-like database access must be resolved before launch.

For Docker Compose instead of Railway/Netlify, use `deploy/compose.yaml`. Perform the same owner migration/grants first, set `.env.production` to the runtime connection with `AUTO_MIGRATE=false`, then run the documented compose command. The API will refuse an unprepared database.

## 3. Complete operator configuration

- Set `OPERATOR_NAME`, `SUPPORT_EMAIL`, and `ADMIN_SUBJECTS`. The email and operator name appear publicly; support and the data notice can be read without signing in. Agree on a deletion-response time and privacy contact handling before inviting users.
- Select fixed/known-price provider models. In particular, replace `openrouter/auto` for the public pilot. Configure a daily estimated dollar budget and a token-price ceiling covering every enabled model, plus provider-side spending limits. Do not assume that a free-tier key guarantees unlimited free service.
- Configure automatic encrypted database backups in the hosting/backup service, retention/expiry, and restricted access. Run an isolated restore drill before launch and periodically afterward. The repository's backup CLI creates/restores dumps; it does not schedule, encrypt, upload or expire them.
- Assign an operator to receive uptime/database/backup-failure alerts and review pending deletion requests. Monitor `/health`; enable alerts on repeated 5xx errors and exhausted budgets. Application logs contain generated request IDs, route templates, status and duration, not prompts, search queries or credentials. Keep host/proxy access logs equally restricted.

## 4. Verify the hosted pilot before inviting users

- Sign in with two disposable accounts in separate browser profiles. Verify history, session links, drafts, polling, progress and exports stay isolated. Check logout/re-login, invalid tokens and ordinary-user denial of administrator routes.
- Keep research sharing off at first. Verify optional opt-in/withdrawal and rehearse conversation deletion with the offline operator command against disposable data.
- Make one deliberately budgeted live AI request and a controlled fallback check, then review usage accounting. All local routine checks use synthetic AI; configured keys alone do not prove availability.
- Check mobile navigation, direct page reloads, request recovery and public help/privacy from a signed-out browser. Verify the support email reaches the designated operator.
- Restore a backup to a new isolated database, verify record counts/event protection, and rehearse rollback. Reconcile completed deletion requests before ever restoring an old snapshot into service; see [operations](operations.md).

Streaming, voice/files, in-conversation search and additional visual polish remain optional later work. They are not hidden launch blockers for the current text-chat pilot.
