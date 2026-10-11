"""POST /api/chat: response contract, input validation, CORS, and error handling."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, app_context

RESPONSE_KEYS = {"answer", "language", "citations", "confidence", "insufficient_evidence", "document_coverage_date"}
CITATION_KEYS = {"document_title", "rule_number", "page_number", "excerpt"}


def _assert_contract(data):
    assert set(data) == RESPONSE_KEYS
    assert isinstance(data["answer"], str) and data["answer"]
    assert data["language"] in ("en", "hi")
    assert data["confidence"] in ("high", "medium", "low")
    assert isinstance(data["insufficient_evidence"], bool)
    assert data["document_coverage_date"] == "2025-03-06"
    assert isinstance(data["citations"], list)
    for c in data["citations"]:
        assert set(c) == CITATION_KEYS
        assert isinstance(c["document_title"], str)
        assert c["rule_number"] is None or isinstance(c["rule_number"], str)
        assert c["page_number"] is None or isinstance(c["page_number"], int)
        assert isinstance(c["excerpt"], str) and c["excerpt"]
    if data["insufficient_evidence"]:
        assert data["citations"] == []


def test_english_request(client):
    r = client.post("/api/chat", json={"question": "What are the building setback requirements for a 10 m wide street?", "language": "en"})
    assert r.status_code == 200
    data = r.json()
    _assert_contract(data)
    assert data["language"] == "en"
    assert data["citations"]


def test_hindi_request(client):
    r = client.post("/api/chat", json={"question": "मेरा प्लॉट 200 वर्ग मीटर का है और सामने 9 मीटर चौड़ी सड़क है। आगे कितनी जगह खाली छोड़नी होगी?", "language": "hi"})
    assert r.status_code == 200
    data = r.json()
    _assert_contract(data)
    assert data["language"] == "hi"


def test_language_optional(client):
    r = client.post("/api/chat", json={"question": "What is the fee for building permission?"})
    assert r.status_code == 200
    assert r.json()["language"] == "en"


def test_insufficient_evidence_contract(client):
    r = client.post("/api/chat", json={"question": "How do I pay my property tax online?", "language": "en"})
    assert r.status_code == 200
    data = r.json()
    _assert_contract(data)
    assert data["insufficient_evidence"] is True


@pytest.mark.parametrize("payload", [
    {"question": "   ", "language": "en"},
    {"question": "", "language": "en"},
    {"language": "en"},
    {"question": None},
    {"question": 123},
    {"question": ["a list"]},
    {"question": "x" * 2001},
    {"question": "What is the fee?", "language": "fr"},
    {"question": "What is the fee?", "language": 5},
])
def test_invalid_input_rejected(client, payload):
    r = client.post("/api/chat", json=payload)
    assert r.status_code == 422
    body = r.json()
    assert body["message"] == "Invalid request parameters."
    assert isinstance(body["detail"], list) and body["detail"]


def test_malformed_json_rejected(client):
    r = client.post("/api/chat", content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_wrong_method(client):
    assert client.get("/api/chat").status_code == 405


def test_cors_allows_configured_dev_origin(client):
    r = client.options("/api/chat", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_allows_vercel_origin(client):
    r = client.options("/api/chat", headers={
        "Origin": "https://bhumi-vikas-shayak-claude-imp-git-a3ea33-anubhavg2210s-projects.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://bhumi-vikas-shayak-claude-imp-git-a3ea33-anubhavg2210s-projects.vercel.app"


def test_cors_rejects_unknown_origin(client):
    r = client.options("/api/chat", headers={
        "Origin": "https://evil.example.com",
        "Access-Control-Request-Method": "POST",
    })
    assert r.headers.get("access-control-allow-origin") is None


def test_internal_error_does_not_leak_details(rag_service, monkeypatch):
    async def boom(request):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(rag_service, "answer_question", boom)
    saved = app_context.rag_service
    app_context.rag_service = rag_service
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.post("/api/chat", json={"question": "What is the fee?"})
    finally:
        app_context.rag_service = saved
    assert r.status_code == 500
    assert "secret" not in r.text
    assert r.json()["message"] == "Internal server error."
