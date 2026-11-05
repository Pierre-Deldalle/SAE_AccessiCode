import asyncio
from accessi_code.ai.clients.llm import OllamaLLM
from accessi_code.ai.clients.vlm import OllamaVLM


def test_llm_caps_generation_without_changing_requested_format(monkeypatch):
    monkeypatch.setenv('ACCESSICODE_AI_TOKEN_CAP', '120')
    client = OllamaLLM('test-model')
    observed = {}

    async def fake_post(endpoint, payload):
        observed.update(payload)
        return {'response': '{"ok": true}'}

    client._post = fake_post
    assert asyncio.run(client.generate('Question', max_tokens=800, format='json'))
    assert observed['options']['num_predict'] == 120
    assert observed['format'] == 'json'


def test_vlm_caps_generation(monkeypatch):
    monkeypatch.setenv('ACCESSICODE_AI_TOKEN_CAP', '100')
    client = OllamaVLM('vision')
    observed = {}

    async def fake_post(endpoint, payload):
        observed.update(payload)
        return {'response': '{"ok": true}'}

    client._post = fake_post
    assert asyncio.run(client.generate('Question', image=b'png', max_tokens=800))
    assert observed['options']['num_predict'] == 100
    assert len(observed['images']) == 1
