import json
import httpx
import pytest
from apps.api import provider


def fake_claude(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key-never-returned')
    monkeypatch.setattr(provider.httpx, 'AsyncClient', lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))


@pytest.mark.parametrize('tier', [1, 2, 3])
def test_real_request_builder_and_response_parser(monkeypatch, tier):
    def handle(request):
        assert str(request.url) == 'https://api.anthropic.com/v1/messages'
        assert request.headers['x-api-key'] == 'test-key-never-returned'
        body = json.loads(request.content)
        context = json.loads(body['messages'][0]['content'])
        assert body['system'] == provider.PROMPTS[tier]
        assert context['problem'] == 'Solve 2x + 3 = 11'
        assert ('attempt' in context) == (tier >= 2)
        assert ('prior_hints' in context) == (tier == 3)
        return httpx.Response(200, json={'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': 'Which operation would isolate the variable?'}]})
    fake_claude(monkeypatch, handle)
    assert provider.generate(tier, 'Solve 2x + 3 = 11', 'Subtract 3', ['Think about inverse operations'], 'anthropic').text == 'Which operation would isolate the variable?'


def test_truncated_response_is_not_delivered_as_complete(monkeypatch):
    fake_claude(monkeypatch, lambda r: httpx.Response(200, json={'stop_reason': 'max_tokens', 'content': [{'type': 'text', 'text': 'An unfinished solution'}]}))
    with pytest.raises(ValueError, match='incomplete response was not delivered'):
        provider.generate(3, 'problem', '', [])


def test_auth_error_is_actionable_and_does_not_leak_key(monkeypatch):
    fake_claude(monkeypatch, lambda r: httpx.Response(401, json={'error': {'message': 'raw provider details'}}))
    with pytest.raises(ValueError, match='Check the API key') as error:
        provider.generate(1, 'problem', '', [])
    assert 'test-key-never-returned' not in str(error.value)
    assert 'raw provider details' not in str(error.value)


@pytest.mark.parametrize('name', ['gemini', 'groq', 'openrouter', 'mistral', 'cloudflare'])
@pytest.mark.parametrize('tier', [1, 2, 3])
def test_selected_provider_sends_only_allowed_context(monkeypatch,name,tier):
    key_env=provider.PROVIDERS[name][1]
    monkeypatch.setenv(key_env,'test-only-key')
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'test-account')
    calls=[]
    answer='Which operation would isolate the variable?'
    def handle(request):
        calls.append(request)
        body=json.loads(request.content)
        if name=='gemini':
            assert request.url.host=='generativelanguage.googleapis.com'
            assert request.headers['x-goog-api-key']=='test-only-key'
            assert 'test-only-key' not in str(request.url)
            assert body['systemInstruction']['parts'][0]['text']==provider.PROMPTS[tier]
            context=json.loads(body['contents'][0]['parts'][0]['text'])
            response={'modelVersion':'reported-test-model','candidates':[{'finishReason':'STOP','content':{'parts':[{'thought':True,'text':'Private reasoning excluded'},{'text':answer}]}}]}
        else:
            assert request.url.host=={'groq':'api.groq.com','openrouter':'openrouter.ai','mistral':'api.mistral.ai','cloudflare':'api.cloudflare.com'}[name]
            assert request.headers['authorization']=='Bearer test-only-key'
            assert body['messages'][0]['content']==provider.PROMPTS[tier]
            context=json.loads(body['messages'][1]['content'])
            response={'model':'reported-test-model','choices':[{'finish_reason':'stop','message':{'content':answer}}]}
        assert context['problem']=='Solve 2x + 3 = 11'
        assert ('attempt' in context)==(tier>=2)
        assert ('prior_hints' in context)==(tier==3)
        return httpx.Response(200,json=response)
    real_client=httpx.AsyncClient
    monkeypatch.setattr(provider.httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handle),**kwargs))
    result=provider.generate(tier,'Solve 2x + 3 = 11','Subtract 3',['Consider inverse operations'],name)
    assert result.text==answer
    assert result.reported_model=='reported-test-model'
    assert len(calls)==1


@pytest.mark.parametrize('name,body',[
    ('gemini',{'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'cut off'}]}}]}),
    ('gemini',{'promptFeedback':{'blockReason':'SAFETY'}}),
    ('groq',{'choices':[{'finish_reason':'length','message':{'content':'cut off'}}]}),
    ('openrouter',{'error':{'message':'Provider failed'}}),
    ('openrouter',{'choices':[]}),
])
def test_unusable_responses_are_rejected(name,body):
    with pytest.raises(ValueError): provider.parse_response(name,body)
