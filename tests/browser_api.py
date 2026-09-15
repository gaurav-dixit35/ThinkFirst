"""Isolated browser-test API. Never use this entry point for participant data."""
import os

if not os.environ.get('DATABASE_URL', '').endswith('/thinkfirst_test'):
    raise RuntimeError('Browser QA requires the dedicated thinkfirst_test database.')
os.environ['AUTH_MODE'] = 'development'
os.environ['ENVIRONMENT'] = 'development'

from apps.api.main import app
from apps.api import provider

# These subprocess-local values override .env, so QA never spends real API usage.
for _, key, _, _ in provider.PROVIDERS.values():
    os.environ[key] = ''
os.environ['CLOUDFLARE_API_KEY'] = ''
os.environ['AI_PROVIDER'] = 'groq'
os.environ['AI_FALLBACK_ENABLED'] = 'true'
os.environ['AI_FALLBACK_ORDER'] = 'groq,gemini,openrouter,mistral,cloudflare'

if os.getenv('QA_MOCK_AI') == 'true':
    import asyncio
    import json
    import httpx
    os.environ['GROQ_API_KEY'] = 'qa-synthetic-key'
    os.environ['GEMINI_API_KEY'] = 'qa-synthetic-key'
    async def handle(request):
        if request.url.host == 'api.groq.com':
            return httpx.Response(429)
        await asyncio.sleep(2)
        body = json.loads(request.content)
        context = json.loads(body['contents'][0]['parts'][0]['text'])
        text = ('Subtracting the same amount preserves equality.' if context.get('followup_question') else
                'Subtract 3, then divide by 2. The result is 4.' if 'prior_hints' in context else
                'Consider inverse operations.' if 'attempt' in context else 'Which operation would isolate the variable?')
        return httpx.Response(200, json={'modelVersion': 'qa-synthetic-model', 'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': text}]}}]})
    client = httpx.AsyncClient
    provider.httpx.AsyncClient = lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs)
