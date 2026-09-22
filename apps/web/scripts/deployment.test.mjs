import test from 'node:test';
import assert from 'node:assert/strict';
import {validateHostedEnvironment} from './deployment.mjs';

test('local workspace stays usable without hosted credentials', () => {
  assert.doesNotThrow(() => validateHostedEnvironment({}));
});
test('hosted website cannot silently use local identity or HTTP API', () => {
  const good = {THINKFIRST_HOSTED:'1', NEXT_PUBLIC_API_URL:'https://api.example.com', NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:'pk_live_placeholder', CLERK_SECRET_KEY:'sk_live_placeholder', CONTEXT:'production'};
  assert.doesNotThrow(() => validateHostedEnvironment(good));
  for (const changes of [
    {NEXT_PUBLIC_API_URL:'http://localhost:8000'},
    {NEXT_PUBLIC_API_URL:'https://key:password@api.example.com'},
    {NEXT_PUBLIC_API_URL:'https://api.example.com/private'},
    {NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:''},
    {NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:'pk_test_placeholder'},
    {CLERK_SECRET_KEY:''},
  ]) assert.throws(() => validateHostedEnvironment({...good, ...changes}));
});
