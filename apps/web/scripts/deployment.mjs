export function validateHostedEnvironment(env) {
  if (env.THINKFIRST_HOSTED !== '1' && env.NETLIFY !== 'true') return;
  let api;
  try { api = new URL(env.NEXT_PUBLIC_API_URL); } catch { /* reported below */ }
  if (!api || api.protocol !== 'https:' || api.username || api.password || api.search || api.hash || api.pathname !== '/') {
    throw new Error('Hosted builds require NEXT_PUBLIC_API_URL as an HTTPS origin, without credentials, paths or query parameters.');
  }
  if (!/^pk_(test|live)_/.test(env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || '')) {
    throw new Error('Hosted builds require NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY. Local shared-account mode cannot be deployed.');
  }
  if (!/^sk_(test|live)_/.test(env.CLERK_SECRET_KEY || '') && env.THINKFIRST_STANDALONE !== '1') {
    throw new Error('Set CLERK_SECRET_KEY in the hosting secret store for authenticated server middleware.');
  }
  if (env.CONTEXT === 'production' && !env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.startsWith('pk_live_')) {
    throw new Error('Use a production Clerk instance for the production website.');
  }
}
