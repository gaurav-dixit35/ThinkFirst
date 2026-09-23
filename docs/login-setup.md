# Account setup

ThinkFirst has dedicated `/login` and `/signup` pages, including nested routes for Clerk verification and recovery steps. Signed-in visitors can open their workspace or sign out to switch accounts. Help and Privacy remain public. Account management lives in Settings. Available authentication methods and password recovery depend on the Clerk application configuration; ThinkFirst does not store passwords.

## Activate locally

1. Create or open a Clerk application in your own dashboard. Use its development instance for local work. Enable the email sign-in/verification method you want. Enable Google only if you want that method and have completed its Clerk setup.
2. In the root `.env`, add `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, and `CLERK_ISSUER` from that same instance. The issuer is the HTTPS Frontend API URL, without a trailing path. Keep `ENVIRONMENT=development`. Do not paste secrets into chat or commit them.
3. From the repository root, run:

   ```powershell
   .\.venv\Scripts\python.exe scripts/setup_auth.py --apply
   ```

   This checks local configuration shape and key/issuer consistency, copies only website authentication settings and the API URL into ignored `apps/web/.env.local`, and sets the API's `AUTH_MODE=clerk`. Existing unrelated settings are preserved. It does not call Clerk, AI providers, or the database, and does not prove credentials are valid. Production environments are refused by this local helper.
4. Restart the API with the root `.env`. In `apps/web`, run `npm run dev`, or `npm run build` followed by `npm run start` for a production build. Use `http://localhost:3000/login`; the helper includes this exact origin in API authorized parties. The npm scripts explicitly bind to `localhost`: binding Next.js to `127.0.0.1` while browsing `localhost` caused a Clerk middleware self-proxy loop and Internal Server Error with this installed version.
5. Sign up with your own account when ready to verify the finished integration. New accounts start with their own workspace. Existing shared development conversations stay with the development identity; they are not moved automatically.

Next.js reads `apps/web/.env.local`, while the API reads root `.env`; adding Clerk values to root `.env` alone does not enable website sign-in. Environment variables supplied by a host/shell take precedence over env files: remove conflicting overrides before restarting. Public Clerk values are embedded at web build time.

## Hosting

Set the website's publishable key and server-only secret in Netlify, and the matching issuer plus `AUTH_MODE=clerk` on the API host. Set exact website/API origins. Use the production Clerk instance and configure the deployed domain in Clerk. See [deployment checklist](deployment-checklist.md). Never put the Clerk secret or AI keys in a `NEXT_PUBLIC_` variable.

The code blocks opening a shared development API as a signed-in personal account if only the website was configured. A failed API authentication shows a sign-in recovery link; the account screen supports signing out and starting again.

## Completion status

Local development Clerk credentials are configured and the API and website have been restarted. Real Clerk login and signup forms rendered successfully in the browser smoke check, including at mobile width. No account was created or signed in by the automated check. Complete signup, verification, recovery, sign-out and two-account isolation with your own accounts before launch. Production credentials and domains remain separate; see [validation](validation.md) for test results.

Reference: [Clerk custom sign-in page](https://clerk.com/docs/nextjs/guides/development/custom-sign-in-or-up-page), [custom signup page](https://clerk.com/docs/nextjs/guides/development/custom-sign-up-page).
