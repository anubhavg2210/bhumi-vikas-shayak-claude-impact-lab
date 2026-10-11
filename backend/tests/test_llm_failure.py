"""LLM provider failures: the API degrades to verified retrieval-only answers, never a 500."""
import httpx
import pytest
from types import SimpleNamespace
from backend.app.models.schemas import ChatRequest
from backend.app.services.llm_provider import (
    AnthropicLLMProvider,
    GeminiLLMProvider,
    LLMConfigurationError,
    LLMProviderError,
    OpenAILLMProvider,
    get_llm_provider,
)

FARM_Q = "I want a farm house on agricultural land. What is the minimum plot size and the maximum FAR?"


@pytest.mark.asyncio
async def test_provider_exception_falls_back_to_verified_passages(scripted_rag):
    svc, _ = scripted_rag(force_failure=True)
    res = await svc.answer_question(ChatRequest(question=FARM_Q, language="en"))
    assert "currently unavailable" in res.answer
    assert res.insufficient_evidence is False
    assert res.citations and res.citations[0].rule_number == "17"
    assert res.citations[0].page_number == 34
    assert res.confidence.value in ("low", "medium")


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [
    "Sorry, I cannot help with that.",                 # no JSON at all
    "{not valid json",                                 # malformed
    '["answer", "citations"]',                         # wrong top-level type
    '{"answer": 42, "citations": []}',                 # wrong field type
    '{"answer": "x", "citations": "Rule 17"}',         # wrong field type
])
async def test_unparseable_output_falls_back(scripted_rag, raw):
    svc, _ = scripted_rag(raw)
    res = await svc.answer_question(ChatRequest(question=FARM_Q))
    assert "currently unavailable" in res.answer
    assert all(c.rule_number == "17" for c in res.citations[:1])


@pytest.mark.asyncio
async def test_json_in_markdown_fence_is_parsed(scripted_rag):
    raw = '```json\n{"answer": "Minimum plot size is 0.40 hectare.", "confidence": "high", "insufficient_evidence": false, ' \
          '"citations": [{"rule_number": "17", "excerpt": "Minimum size of the plot shall be 0.40 hectare;"}]}\n```'
    svc, _ = scripted_rag(raw)
    res = await svc.answer_question(ChatRequest(question=FARM_Q))
    assert res.answer.startswith("Minimum plot size")
    assert res.confidence.value == "high"


def test_endpoint_returns_200_when_provider_fails(client, scripted_rag):
    from backend.app.main import app_context
    svc, _ = scripted_rag(force_failure=True)
    original = app_context.rag_service
    app_context.rag_service = svc
    try:
        r = client.post("/api/chat", json={"question": FARM_Q, "language": "en"})
    finally:
        app_context.rag_service = original
    assert r.status_code == 200
    assert r.json()["citations"][0]["rule_number"] == "17"


# ----------------------------------------------------------- HTTP providers

def _transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_openai_http_error_raises_provider_error():
    p = OpenAILLMProvider(api_key="test", transport=_transport(lambda req: httpx.Response(500, text="boom")))
    with pytest.raises(LLMProviderError, match="HTTP 500"):
        await p.generate_response("s", "u")


@pytest.mark.asyncio
async def test_openai_timeout_raises_provider_error():
    def handler(req):
        raise httpx.ReadTimeout("timed out", request=req)
    p = OpenAILLMProvider(api_key="test", transport=_transport(handler))
    with pytest.raises(LLMProviderError, match="Network error"):
        await p.generate_response("s", "u")


@pytest.mark.asyncio
async def test_openai_success_and_bad_shape():
    ok = OpenAILLMProvider(api_key="k", transport=_transport(
        lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "{\"answer\": \"x\"}"}}]})))
    assert await ok.generate_response("s", "u") == '{"answer": "x"}'
    bad = OpenAILLMProvider(api_key="k", transport=_transport(lambda req: httpx.Response(200, json={"unexpected": True})))
    with pytest.raises(LLMProviderError, match="Unexpected"):
        await bad.generate_response("s", "u")


@pytest.mark.asyncio
async def test_missing_api_keys_raise_provider_error(monkeypatch):
    from backend.app.config import settings
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    with pytest.raises(LLMProviderError):
        await OpenAILLMProvider(api_key=None).generate_response("s", "u")
    with pytest.raises(LLMProviderError):
        await GeminiLLMProvider(api_key=None).generate_response("s", "u")


@pytest.mark.asyncio
async def test_gemini_sends_key_in_header_not_url():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["key"] = req.headers.get("x-goog-api-key")
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}]})

    p = GeminiLLMProvider(api_key="secret-key", transport=_transport(handler))
    assert await p.generate_response("s", "u") == "{}"
    assert "secret-key" not in seen["url"]
    assert seen["key"] == "secret-key"


@pytest.mark.asyncio
async def test_gemini_safety_block_raises():
    p = GeminiLLMProvider(api_key="k", transport=_transport(
        lambda req: httpx.Response(200, json={"candidates": [{"finishReason": "SAFETY", "content": {"parts": []}}]})))
    with pytest.raises(LLMProviderError, match="SAFETY"):
        await p.generate_response("s", "u")


# ----------------------------------------------------------- Anthropic (SDK client faked)

class _FakeMessages:
    def __init__(self, response=None, exc=None):
        self.response, self.exc, self.kwargs = response, exc, None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        if self.exc:
            raise self.exc
        return self.response


def _fake_anthropic(response=None, exc=None):
    messages = _FakeMessages(response, exc)
    return SimpleNamespace(messages=messages, beta=SimpleNamespace(messages=messages)), messages


@pytest.mark.asyncio
async def test_anthropic_extracts_text_blocks_and_omits_sampling_params():
    response = SimpleNamespace(stop_reason="end_turn", content=[
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="text", text='{"answer": "ok"}'),
    ])
    client, messages = _fake_anthropic(response)
    out = await AnthropicLLMProvider(client=client, model="claude-opus-5-5").generate_response("sys", "user")
    assert out == '{"answer": "ok"}'
    assert messages.kwargs["model"] == "claude-opus-5-5"
    assert "temperature" not in messages.kwargs  # rejected by Claude Opus 5.5
    assert messages.kwargs["system"] == "sys"


@pytest.mark.asyncio
async def test_anthropic_refusal_raises():
    client, _ = _fake_anthropic(SimpleNamespace(stop_reason="refusal", content=[]))
    with pytest.raises(LLMProviderError, match="refusal"):
        await AnthropicLLMProvider(client=client).generate_response("s", "u")


@pytest.mark.asyncio
async def test_anthropic_api_exception_wrapped():
    client, _ = _fake_anthropic(exc=RuntimeError("connection reset"))
    with pytest.raises(LLMProviderError, match="RuntimeError"):
        await AnthropicLLMProvider(client=client).generate_response("s", "u")


# ----------------------------------------------------------- factory

def test_provider_factory():
    assert get_llm_provider("extractive") is None
    assert get_llm_provider("mock") is None  # legacy alias
    assert isinstance(get_llm_provider("openai"), OpenAILLMProvider)
    assert isinstance(get_llm_provider("anthropic"), AnthropicLLMProvider)
    with pytest.raises(LLMConfigurationError):
        get_llm_provider("not-a-provider")
