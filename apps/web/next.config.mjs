import {validateHostedEnvironment} from './scripts/deployment.mjs';
if (process.env.THINKFIRST_QA === '1' && (process.env.NETLIFY === 'true' || process.env.THINKFIRST_HOSTED === '1')) throw new Error('The isolated QA build cannot be deployed.');
validateHostedEnvironment(process.env);

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  distDir: process.env.THINKFIRST_QA === '1' ? '.next-qa' : '.next',
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
