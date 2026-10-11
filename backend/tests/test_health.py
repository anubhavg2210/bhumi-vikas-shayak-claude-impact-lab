"""GET /health, GET /, and GET /api/coverage."""


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["document_coverage_date"] == "2025-03-06"
    assert data["documents_loaded"] == 106
    assert data["provider"] == "extractive"
    assert data["version"] == "1.0.0"


def test_root_endpoint(client):
    data = client.get("/").json()
    assert "Bhumi Vikas Sahayak" in data["name"]
    assert data["document_coverage_date"] == "2025-03-06"
    assert data["health_check"] == "/health"


def test_coverage_endpoint(client):
    r = client.get("/api/coverage")
    assert r.status_code == 200
    data = r.json()
    assert data["document_coverage_date"] == "2025-03-06"
    assert data["documents_loaded"] == 106
    amendments = data["known_post_coverage_amendments"]
    assert any(a["provision"] == "Rule 2(5)(c)" and a["date"] == "2026-08-28" and a["in_collection"] is False
               for a in amendments)
    assert data["limitations"]
