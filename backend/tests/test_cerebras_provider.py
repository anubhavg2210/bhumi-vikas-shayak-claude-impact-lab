"""Cerebras Cloud provider: the real `openai` SDK is exercised against a mocked HTTP transport
(no network, no API key needed), both on its own and through the RAG pipeline and /api/chat."""
import html
import json
import re
import httpx2
import pytest
from fastapi.testclient import TestClient
from backend.app.config import DEFAULT_CEREBRAS_MODEL, Settings, settings
from backend.app.main import app, app_context
from backend.app.models.schemas import ChatRequest
from backend.app.services.document_store import normalize_text
from backend.app.services.llm_provider import CerebrasLLMProvider, LLMProviderError, get_llm_provider
from backend.app.services.rag_service import ANSWER_JSON_SCHEMA, SYSTEM_PROMPT

TEST_KEY = "csk-test-SECRET-0000"
CHAT_URL = "https://api.cerebras.ai/v1/chat/completions"
FRONT_Q = "My house faces a 10 m wide street and will be 9 m tall. How much open space do I leave at the front?"
FRONT_ROW = "More than 9.0 meters and up to 12 meters 3.6 meters"
Q14_HI = "मेरा प्लॉट 200 वर्ग मीटर का है और सामने 9 मीटर चौड़ी सड़क है। आगे कितनी जगह खाली छोड़नी होगी?"
NINE_M_ROW = "Up to 9.0 meters 3.0 meters"


# ------------------------------------------------------------------ helpers

def completion(content, finish_reason="stop", reasoning=None):
    message = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning"] = reasoning
    return {
        "id": "chatcmpl-test", "object": "chat.completion", "created": 1, "model": DEFAULT_CEREBRAS_MODEL,
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def passages_in(request):
    """Return {passage_id: text} from the user prompt the backend sent to Cerebras."""
    user = json.loads(request.content)["messages"][1]["content"]
    blocks = re.findall(r'<untrusted_document_context id="(\d+)"[^>]*>\n(.*?)\n</untrusted_document_context>', user, re.S)
    return {int(i): html.unescape(t) for i, t in blocks}


def passage_containing(request, needle):
    for pid, text in passages_in(request).items():
        if normalize_text(needle) in normalize_text(text):
            return pid
    raise AssertionError(f"no passage sent to the model contains {needle!r}")


class Recorder:
    """Mock transport handler that records requests and returns scripted responses."""

    def __init__(self, responder):
        self.responder = responder
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return self.responder(request)


@pytest.fixture(autouse=True)
def no_sdk_retries(monkeypatch):
    monkeypatch.setattr(settings, "CEREBRAS_MAX_RETRIES", 0)
    monkeypatch.setattr(settings, "CEREBRAS_REASONING_EFFORT", None)
    monkeypatch.setattr(settings, "CEREBRAS_TEMPERATURE", None)


def make_provider(responder, api_key=TEST_KEY, model=None):
    rec = Recorder(responder)
    provider = CerebrasLLMProvider(
        api_key=api_key, model=model or DEFAULT_CEREBRAS_MODEL,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(rec)),
    )
    return provider, rec


def json_response(payload, status=200, headers=None):
    return lambda request: httpx2.Response(status, json=payload, headers=headers or {})


# ------------------------------------------------------------------ provider unit tests

@pytest.mark.asyncio
async def test_successful_request_shape():
    provider, rec = make_provider(json_response(completion('{"answer": "ok"}')))
    out = await provider.generate_response("SYS", "USER", json_schema=ANSWER_JSON_SCHEMA)
    assert out == '{"answer": "ok"}'

    req = rec.requests[0]
    assert str(req.url) == CHAT_URL
    assert req.headers["authorization"] == f"Bearer {TEST_KEY}"
    body = json.loads(req.content)
    assert body["model"] == DEFAULT_CEREBRAS_MODEL
    assert body["messages"] == [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USER"}]
    assert body["max_completion_tokens"] == settings.CEREBRAS_MAX_COMPLETION_TOKENS
    assert "max_tokens" not in body  # alias; Cerebras rejects sending both
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == ANSWER_JSON_SCHEMA
    assert "temperature" not in body and "reasoning_effort" not in body


@pytest.mark.asyncio
async def test_optional_parameters_sent_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "CEREBRAS_REASONING_EFFORT", "low")
    monkeypatch.setattr(settings, "CEREBRAS_TEMPERATURE", 0.2)
    provider, rec = make_provider(json_response(completion("{}")), model="qwen-3.8-27b")
    await provider.generate_response("s", "u")
    body = json.loads(rec.requests[0].content)
    assert body["model"] == "qwen-3.8-27b"
    assert body["reasoning_effort"] == "low"
    assert body["temperature"] == 0.2
    assert body["response_format"] == {"type": "json_object"}  # no schema given


@pytest.mark.asyncio
async def test_reasoning_text_is_not_returned():
    provider, _ = make_provider(json_response(completion('{"answer": "final"}', reasoning="private chain of thought")))
    out = await provider.generate_response("s", "u")
    assert out == '{"answer": "final"}'


@pytest.mark.asyncio
async def test_missing_api_key_makes_no_request(monkeypatch):
    # The openai SDK would otherwise fall back to OPENAI_API_KEY; that must not happen.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-should-not-be-used")
    monkeypatch.setattr(settings, "CEREBRAS_API_KEY", None)
    provider, rec = make_provider(json_response(completion("{}")), api_key="")
    assert provider.is_configured() is False
    with pytest.raises(LLMProviderError) as ei:
        await provider.generate_response("s", "u")
    assert ei.value.reason == "not_configured"
    assert rec.requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body,reason,hint", [
    (401, {"message": f"Wrong API Key {TEST_KEY}", "code": "wrong_api_key"}, "auth", "CEREBRAS_API_KEY"),
    (403, {"message": "forbidden"}, "auth", "access"),
    (404, {"message": "Model does not exist", "code": "model_not_found"}, "model_not_found", "CEREBRAS_MODEL"),
    (400, {"message": "unsupported response_format"}, "bad_request", "parameter"),
    (422, {"message": "bad"}, "bad_request", "parameter"),
    (429, {"message": "Too many requests"}, "rate_limited", "rate limit"),
    (402, {"message": "payment required"}, "billing", "billing"),
    (500, {"message": "internal"}, "server_error", "HTTP 500"),
    (503, {"message": "unavailable"}, "server_error", "HTTP 503"),
])
async def test_http_errors_are_classified_without_leaking_the_key(status, body, reason, hint):
    provider, _ = make_provider(json_response(body, status=status))
    with pytest.raises(LLMProviderError) as ei:
        await provider.generate_response("s", "u")
    err = ei.value
    assert err.reason == reason
    assert hint in str(err)
    assert TEST_KEY not in str(err) and "SECRET" not in str(err)
    assert err.__cause__ is None and err.__suppress_context__  # SDK message not chained


@pytest.mark.asyncio
async def test_model_not_found_includes_provider_code():
    provider, _ = make_provider(json_response({"message": "x", "code": "model_not_found"}, status=404), model="no-such-model")
    with pytest.raises(LLMProviderError) as ei:
        await provider.generate_response("s", "u")
    assert "no-such-model" in str(ei.value) and "code=model_not_found" in str(ei.value)


@pytest.mark.asyncio
async def test_rate_limit_is_retried_by_sdk_then_reported(monkeypatch):
    monkeypatch.setattr(settings, "CEREBRAS_MAX_RETRIES", 1)
    provider, rec = make_provider(json_response({"message": "slow down"}, status=429, headers={"retry-after-ms": "1"}))
    with pytest.raises(LLMProviderError) as ei:
        await provider.generate_response("s", "u")
    assert ei.value.reason == "rate_limited"
    assert len(rec.requests) == 2  # original + 1 retry


@pytest.mark.asyncio
async def test_timeout():
    def raise_timeout(request):
        raise httpx2.ReadTimeout("timed out", request=request)
    provider, _ = make_provider(raise_timeout)
    with pytest.raises(LLMProviderError) as ei:
        await provider.generate_response("s", "u")
    assert ei.value.reason == "timeout"


@pytest.mark.asyncio
async def test_network_error():
    def raise_connect(request):
        raise httpx2.ConnectError("connection refused", request=request)
    provider, _ = make_provider(raise_connect)
    with pytest.raises(LLMProviderError) as ei:
        await provider.generate_response("s", "u")
    assert ei.value.reason == "network"


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,reason", [
    (completion('{"answer": "cut', finish_reason="length"), "truncated"),
    (completion("", finish_reason="content_filter"), "refusal"),
    (completion(""), "bad_response"),
    (completion(None), "bad_response"),
    ({"id": "x", "object": "chat.completion", "choices": []}, "bad_response"),
    ({"unexpected": True}, "bad_response"),
])
async def test_unexpected_responses(payload, reason):
    provider, _ = make_provider(json_response(payload))
    with pytest.raises(LLMProviderError) as ei:
        await provider.generate_response("s", "u")
    assert ei.value.reason == reason


def test_factory_and_configuration(monkeypatch):
    monkeypatch.setattr(settings, "CEREBRAS_API_KEY", None)
    provider = get_llm_provider("cerebras")
    assert isinstance(provider, CerebrasLLMProvider)
    assert provider.is_configured() is False
    assert provider.base_url == "https://api.cerebras.ai/v1"


def test_settings_blank_placeholders(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "")
    monkeypatch.setenv("CEREBRAS_MODEL", "")
    monkeypatch.setenv("CEREBRAS_TEMPERATURE", "")
    monkeypatch.setenv("CEREBRAS_REASONING_EFFORT", "")
    s = Settings(_env_file=None)
    assert s.CEREBRAS_API_KEY is None
    assert s.CEREBRAS_MODEL == DEFAULT_CEREBRAS_MODEL
    assert s.CEREBRAS_TEMPERATURE is None and s.CEREBRAS_REASONING_EFFORT is None
    monkeypatch.setenv("CEREBRAS_MODEL", " qwen-3.8-27b ")
    assert Settings(_env_file=None).CEREBRAS_MODEL == "qwen-3.8-27b"


def test_answer_schema_is_cerebras_strict_compatible():
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node["required"]) <= set(node["properties"])
            assert not {"maxItems", "minItems", "pattern", "format", "oneOf", "allOf"} & set(node)
            for v in node.values():
                walk(v)
    walk(ANSWER_JSON_SCHEMA)


def test_system_prompt_grounding_requirements():
    for phrase in ["untrusted_document_context", "Never invent", "conditions and exceptions",
                   "incomplete, ambiguous", "not a building-plan approval", "requested language",
                   "double quotes", "passage_id"]:
        assert phrase in SYSTEM_PROMPT, phrase


# ------------------------------------------------------------------ through the RAG pipeline

def scripted_cerebras(answer_for):
    """Responder that builds a model answer from the passages actually sent in the request."""
    def responder(request):
        return httpx2.Response(200, json=completion(json.dumps(answer_for(request), ensure_ascii=False)))
    return responder


@pytest.fixture
def cerebras_rag(make_rag):
    def _make(responder):
        provider, rec = make_provider(responder)
        return make_rag(provider), rec
    return _make


@pytest.mark.asyncio
async def test_english_answer_with_citation_from_retrieval_record(cerebras_rag):
    svc, rec = cerebras_rag(scripted_cerebras(lambda req: {
        "answer": f'Rule 56 says "{FRONT_ROW}". Explanation: for a 10 m street the front open space is 3.6 meters.',
        "confidence": "high", "insufficient_evidence": False,
        "citations": [{"passage_id": passage_containing(req, FRONT_ROW), "quote": FRONT_ROW}],
    }))
    res = await svc.answer_question(ChatRequest(question=FRONT_Q, language="en"))
    assert res.language == "en" and res.insufficient_evidence is False
    assert res.confidence.value == "high"
    cit = res.citations[0]
    assert (cit.rule_number, cit.page_number, cit.excerpt) == ("56", 77, FRONT_ROW)
    assert cit.document_title == settings.DOCUMENT_TITLE
    user_prompt = json.loads(rec.requests[0].content)["messages"][1]["content"]
    assert "Requested answer language: English" in user_prompt


@pytest.mark.asyncio
async def test_hindi_answer(cerebras_rag):
    svc, rec = cerebras_rag(scripted_cerebras(lambda req: {
        "answer": f'नियम 56 में लिखा है: "{NINE_M_ROW}"। व्याख्या: 9 मीटर तक चौड़ी सड़क के लिए न्यूनतम अग्र खुला स्थान 3.0 मीटर है।',
        "confidence": "high", "insufficient_evidence": False,
        "citations": [{"passage_id": passage_containing(req, NINE_M_ROW), "quote": NINE_M_ROW}],
    }))
    res = await svc.answer_question(ChatRequest(question=Q14_HI, language="hi"))
    assert res.language == "hi" and res.insufficient_evidence is False
    assert "व्याख्या" in res.answer
    assert res.citations[0].rule_number == "56" and res.citations[0].page_number == 77
    assert "Requested answer language: Hindi" in json.loads(rec.requests[0].content)["messages"][1]["content"]


@pytest.mark.asyncio
async def test_empty_passage_quote_cites_whole_passage(cerebras_rag):
    svc, _ = cerebras_rag(scripted_cerebras(lambda req: {
        "answer": "The front open space depends on street width; for 10 m it is 3.6 meters.",
        "confidence": "medium", "insufficient_evidence": False,
        "citations": [{"passage_id": passage_containing(req, FRONT_ROW), "quote": ""}],
    }))
    res = await svc.answer_question(ChatRequest(question=FRONT_Q))
    assert res.citations[0].rule_number == "56"
    assert "3.6 meters" in res.citations[0].excerpt


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_citation", [
    {"passage_id": 99, "quote": FRONT_ROW},                                   # not a passage that was sent
    {"passage_id": 0, "quote": FRONT_ROW},
    {"passage_id": "abc", "quote": FRONT_ROW},
    {"passage_id": 1, "quote": "Front open space shall be 1 meter for all streets."},  # not in the passage
])
async def test_invalid_citations_are_rejected(cerebras_rag, bad_citation):
    svc, _ = cerebras_rag(scripted_cerebras(lambda req: {
        "answer": "The front open space is 1 meter.", "confidence": "high",
        "insufficient_evidence": False, "citations": [bad_citation],
    }))
    res = await svc.answer_question(ChatRequest(question=FRONT_Q))
    assert res.insufficient_evidence is True
    assert res.citations == []
    assert "1 meter" not in res.answer


@pytest.mark.asyncio
async def test_model_supplied_metadata_is_ignored(cerebras_rag):
    svc, _ = cerebras_rag(scripted_cerebras(lambda req: {
        "answer": "3.6 meters.", "confidence": "high", "insufficient_evidence": False,
        "citations": [{"passage_id": passage_containing(req, FRONT_ROW), "quote": FRONT_ROW,
                       "rule_number": "999", "page_number": 5, "document_title": "Fake Act"}],
    }))
    res = await svc.answer_question(ChatRequest(question=FRONT_Q))
    cit = res.citations[0]
    assert (cit.rule_number, cit.page_number, cit.document_title) == ("56", 77, settings.DOCUMENT_TITLE)


@pytest.mark.asyncio
@pytest.mark.parametrize("question", [
    "What is the cricket score today?",            # nothing relevant retrieved
    "What is the recipe for butter chicken?",
    "How do I pay my property tax online?",        # out of scope
])
async def test_no_relevant_evidence_means_no_model_call(cerebras_rag, question):
    svc, rec = cerebras_rag(scripted_cerebras(lambda req: {"answer": "invented", "confidence": "high",
                                                           "insufficient_evidence": False, "citations": []}))
    res = await svc.answer_question(ChatRequest(question=question))
    assert rec.requests == []
    assert res.insufficient_evidence is True and res.citations == []
    assert "invented" not in res.answer


@pytest.mark.asyncio
async def test_only_relevant_passages_are_sent(cerebras_rag, retriever):
    svc, rec = cerebras_rag(scripted_cerebras(lambda req: {"answer": "x", "confidence": "low",
                                                           "insufficient_evidence": True, "citations": []}))
    await svc.answer_question(ChatRequest(question=FRONT_Q))
    sent = passages_in(rec.requests[0])
    assert sent and all(r.confidence != "low" for r in retriever.retrieve(FRONT_Q, top_k=len(sent)))


@pytest.mark.asyncio
async def test_model_reports_insufficient_evidence(cerebras_rag):
    svc, _ = cerebras_rag(scripted_cerebras(lambda req: {
        "answer": "The supplied passages do not state whether the fee can be paid by UPI.",
        "confidence": "low", "insufficient_evidence": True, "citations": [],
    }))
    res = await svc.answer_question(ChatRequest(question="Can the building permission fee be paid online by UPI?"))
    assert res.insufficient_evidence is True and res.citations == []
    assert "UPI" in res.answer


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 404, 429, 500])
async def test_provider_failure_returns_clear_unavailable_response(cerebras_rag, status):
    svc, _ = cerebras_rag(json_response({"message": f"error mentioning {TEST_KEY}"}, status=status))
    res = await svc.answer_question(ChatRequest(question=FRONT_Q))
    assert res.answer.startswith("The AI answer service is currently unavailable.")
    assert res.confidence.value == "low"
    assert TEST_KEY not in res.answer
    # Only verified source passages are returned; nothing generated.
    assert res.citations and all(c.rule_number == "56" for c in res.citations)


@pytest.mark.asyncio
async def test_provider_timeout_in_hindi(cerebras_rag):
    def raise_timeout(request):
        raise httpx2.ReadTimeout("timed out", request=request)
    svc, _ = cerebras_rag(raise_timeout)
    res = await svc.answer_question(ChatRequest(question=Q14_HI))
    assert res.language == "hi"
    assert res.answer.startswith("एआई उत्तर सेवा अभी उपलब्ध नहीं है।")


# ------------------------------------------------------------------ API compatibility

@pytest.fixture
def cerebras_client(make_rag):
    def _make(responder, api_key=TEST_KEY):
        provider, rec = make_provider(responder, api_key=api_key)
        saved = app_context.rag_service
        app_context.rag_service = make_rag(provider)
        return TestClient(app), rec, saved
    return _make


def test_chat_api_contract_with_cerebras(cerebras_client, caplog):
    client, rec, saved = cerebras_client(scripted_cerebras(lambda req: {
        "answer": "3.6 meters.", "confidence": "high", "insufficient_evidence": False,
        "citations": [{"passage_id": passage_containing(req, FRONT_ROW), "quote": FRONT_ROW}],
    }))
    try:
        with client:
            r = client.post("/api/chat", json={"question": FRONT_Q, "language": "en"})
            health = client.get("/health").json()
    finally:
        app_context.rag_service = saved
    assert r.status_code == 200
    data = r.json()
    assert set(data) == {"answer", "language", "citations", "confidence", "insufficient_evidence", "document_coverage_date"}
    assert set(data["citations"][0]) == {"document_title", "rule_number", "page_number", "excerpt"}
    assert data["citations"][0]["rule_number"] == "56"
    assert data["document_coverage_date"] == "2025-03-06"
    assert health["provider"] == "cerebras" and health["status"] == "healthy"
    assert TEST_KEY not in caplog.text


def test_health_degraded_without_key(cerebras_client):
    client, rec, saved = cerebras_client(json_response(completion("{}")), api_key="")
    try:
        with client:
            health = client.get("/health").json()
            r = client.post("/api/chat", json={"question": FRONT_Q})
    finally:
        app_context.rag_service = saved
    assert health["status"] == "degraded" and health["provider"] == "cerebras"
    assert r.status_code == 200 and r.json()["answer"].startswith("The AI answer service is currently unavailable.")
    assert rec.requests == []
