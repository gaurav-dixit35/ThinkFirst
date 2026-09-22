"""Aggregate provider SSE while exposing only answer text, never reasoning deltas."""
import json


async def read(response, name, on_delta):
    text, model, finish, usage, ended = '', None, None, None, False
    data = []
    async def packets():
        async for line in response.aiter_lines():
            if len(line) > 262144:
                raise ValueError('The provider stream exceeded its size limit.')
            if line.startswith('data:'):
                data.append(line[5:].lstrip())
            elif not line and data:
                yield '\n'.join(data)
                data.clear()
        if data:
            yield '\n'.join(data)
    async for raw in packets():
        if raw == '[DONE]':
            ended = True
            continue
        item = json.loads(raw)
        if item.get('error') or item.get('type') == 'error':
            raise ValueError('The provider interrupted this response.')
        delta = ''
        if name == 'gemini':
            model = item.get('modelVersion', model)
            usage = item.get('usageMetadata', usage)
            candidates = item.get('candidates') or []
            if item.get('promptFeedback', {}).get('blockReason'):
                from .provider import ProviderError
                raise ProviderError('This request could not be answered.', 'content_filter', recoverable=False)
            if candidates:
                candidate = candidates[0]
                delta = ''.join(p.get('text', '') for p in candidate.get('content', {}).get('parts', []) if not p.get('thought'))
                finish = candidate.get('finishReason', finish)
                ended = ended or finish is not None
        elif name == 'anthropic':
            kind = item.get('type')
            if kind == 'message_start':
                message = item.get('message', {})
                model, usage = message.get('model'), message.get('usage')
            elif kind == 'content_block_delta' and item.get('delta', {}).get('type') == 'text_delta':
                delta = item['delta']['text']
            elif kind == 'message_delta':
                finish = item.get('delta', {}).get('stop_reason', finish)
                usage = {**(usage or {}), **(item.get('usage') or {})}
            elif kind == 'message_stop':
                ended = True
        else:
            model = item.get('model', model)
            usage = item.get('usage') or item.get('x_groq', {}).get('usage') or usage
            choices = item.get('choices') or []
            if choices:
                change = choices[0].get('delta') or {}
                if change.get('refusal'):
                    from .provider import ProviderError
                    raise ProviderError('This request could not be answered.', 'content_filter', recoverable=False)
                delta = change.get('content') or ''
                finish = choices[0].get('finish_reason') or finish
        if not isinstance(delta, str):
            raise ValueError('Invalid provider text delta.')
        text += delta
        if len(text) > 100000:
            raise ValueError('The provider answer exceeded its size limit.')
        if delta:
            on_delta(text)
    if not ended or not finish:
        raise ValueError('The response stream ended before completion.')
    if name == 'gemini':
        return {'candidates':[{'content':{'parts':[{'text':text}]}, 'finishReason':finish}], 'modelVersion':model, 'usageMetadata':usage}
    if name == 'anthropic':
        return {'content':[{'type':'text','text':text}], 'stop_reason':finish, 'model':model, 'usage':usage}
    return {'choices':[{'message':{'content':text}, 'finish_reason':finish}], 'model':model, 'usage':usage}
