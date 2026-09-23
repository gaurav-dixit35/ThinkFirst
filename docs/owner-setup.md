# What is needed from the project owner

The useful feature batch is implemented locally. External accounts, production configuration, and real hosted verification remain. Do not put secrets in chat, commits, screenshots, or issue reports.

## 1. Activate local login first

Local activation and real login/signup form rendering were verified on September 23, 2026. You do not need to enter the existing keys again. Open `http://localhost:3000/signup` to create your own account; steps below remain the setup reference for a fresh installation.

1. Open the [Clerk dashboard](https://dashboard.clerk.com/) and create/select the ThinkFirst application. Select the **Development** instance for localhost.
2. Choose your sign-in methods. Email is sufficient to start; Google can be enabled separately.
3. Open the application's API keys section. Copy the publishable key and secret key into the existing root `.env` as `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY`. Set `CLERK_ISSUER` to that instance's HTTPS Frontend API URL, with no additional path. All three must come from the same instance.
4. Keep `ENVIRONMENT=development`. From `D:\res`, run:

   ```powershell
   .\.venv\Scripts\python.exe scripts/setup_auth.py --apply
   ```

5. Restart the API, then rebuild/restart the website (or restart the Next development server). Open `http://localhost:3000/signup`. Existing shared-workspace conversations do not move to a new personal account.
6. After signing up, find your own Clerk user ID in the application's Users section. Put that exact `user_...` identifier in the API's `ADMIN_SUBJECTS`, then restart the API. This enables operator reports/deletion controls for your account. Do not grant every user administrator access.

References: [Clerk keys](https://clerk.com/docs/guides/secure/rotate-api-keys), [Clerk Frontend API and environments](https://clerk.com/docs/guides/how-clerk-works/overview), [local setup details](login-setup.md).

## 2. Supply public operator details

Decide the public operator name and a monitored support email address. Add them to the API environment as `OPERATOR_NAME` and `SUPPORT_EMAIL`. These are shown publicly in Help and Privacy. Decide who checks support/deletion reports and how frequently. Stored reports do not send email automatically.

## 3. Choose the spending limits

Provide an AI daily budget and a hosting monthly budget. The request/token/concurrency limits already exist; the estimated dollar cap is currently disabled locally. A monetary ceiling requires a conservative per-token price ceiling for the models you actually use; configure provider-side limits as well. We will not invent a price or claim that a free tier guarantees continuous service.

Your existing provider keys do not need to be pasted again. Their configuration does not prove available credits or real connectivity. One deliberately budgeted live answer/fallback check remains before public launch.

## 4. Prepare production hosting and domains

1. Make the project available in your own Git repository, excluding `.env`, `.env.local`, database backups and private exports.
2. Prepare a Netlify project for the website and Railway API/PostgreSQL services. The repository already contains `netlify.toml` and `apps/api/Dockerfile`; configure Railway's Dockerfile path as `apps/api/Dockerfile` with repository root as build context.
3. Choose a website domain you control and provide access to its DNS configuration. Clerk production uses its Frontend API under your domain. Hosted preview domains can be used with development Clerk keys for staging, but this repository deliberately requires live Clerk keys for Netlify production builds. Use a separate staging context or configure the production domain; do not bypass the production guard.
4. Create the Clerk **Production** instance and complete its domain/DNS setup. Configure separate production OAuth credentials if using social sign-in. These are separate from the development keys above.
5. Set website values from `deploy/web.env.example` in Netlify. Set API values from `deploy/api.env.example` in Railway. The final website origin becomes `WEB_ORIGINS`; the HTTPS API origin becomes `NEXT_PUBLIC_API_URL`. Public build-time values require a rebuild when changed.
6. Use a separate production database and restricted API database role. Follow [deployment checklist](deployment-checklist.md) to run owner migrations and grant runtime access. This batch adds `learning_preferences` and `support_reports`; earlier text-chat tables are also required. Do not connect the running API with the owner's database credentials.
7. Select and configure backup retention, encrypted backup storage, restoration checks and an uptime/error alert destination. The repository provides backup/restore commands but cannot schedule a host's backups or receive alerts without that external setup.

References: [Netlify environment variables](https://docs.netlify.com/build/environment-variables/get-started/), [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles), [Railway PostgreSQL](https://docs.railway.com/databases/postgresql), [Clerk environments and domains](https://clerk.com/docs/guides/development/managing-environments).

## 5. Final activation walkthrough

Once credentials, domains, budgets and services are configured, verify real signup, email verification/recovery, sign-out and two-account isolation in separate browser profiles. Verify the selected languages with the actual configured models and perform a deliberately limited live provider/fallback check. Confirm operator report handling and backup/restore operations. Synthetic tests do not replace those hosted checks.

No external service was provisioned or deployed as part of this coding batch. Local completion is not a claim that production login, hosted backups or provider billing are already configured.
