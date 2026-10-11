"""Settings parsing."""
import pytest
from backend.app.config import DEFAULT_CORS_ORIGINS, Settings


def test_default_cors_has_no_wildcard():
    s = Settings(_env_file=None)
    assert "*" not in s.CORS_ORIGINS
    assert s.CORS_ORIGINS == DEFAULT_CORS_ORIGINS


@pytest.mark.parametrize("raw,expected", [
    ("http://localhost:3000, http://localhost:5173", ["http://localhost:3000", "http://localhost:5173"]),
    ('["http://a.test", "http://b.test"]', ["http://a.test", "http://b.test"]),
    ("", []),
])
def test_cors_origins_parsing(monkeypatch, raw, expected):
    monkeypatch.setenv("CORS_ORIGINS", raw)
    assert Settings(_env_file=None).CORS_ORIGINS == expected


def test_default_provider_is_extractive():
    assert Settings(_env_file=None).LLM_PROVIDER == "extractive"
