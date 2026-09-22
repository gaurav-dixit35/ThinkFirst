import {validateHostedEnvironment} from './scripts/deployment.mjs';
validateHostedEnvironment(process.env);

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  poweredByHeader: false,
  ...(process.env.THINKFIRST_STANDALONE === '1' ? {output: 'standalone'} : {}),
  async headers() {
    return [{source: '/:path*', headers: [
      {key: 'X-Content-Type-Options', value: 'nosniff'},
      {key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin'},
      {key: 'X-Frame-Options', value: 'DENY'},
      {key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()'},
    ]}];
  },
};
export default config;
