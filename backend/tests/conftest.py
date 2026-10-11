"""Pytest configuration and fixtures for Bhumi Vikas Sahayak tests.

No test calls a real LLM. Scripted MockLLMProvider responses are built from excerpts
that exist verbatim in data/bhumi_vikas_rules.jsonl.
"""
import json
from typing import List, Optional
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, app_context
from backend.app.services.citation_validator import CitationValidator
from backend.app.services.document_store import DocumentStore
from backend.app.services.llm_provider import MockLLMProvider
from backend.app.services.rag_service import RAGService
from backend.app.services.retriever import RuleRetriever


def llm_json(answer: str, citations: Optional[List[dict]] = None, confidence: str = "high",
             insufficient: bool = False) -> str:
    """Build a scripted LLM response in the format the system prompt requests."""
    return json.dumps(
        {"answer": answer, "confidence": confidence, "insufficient_evidence": insufficient,
         "citations": citations or []},
        ensure_ascii=False,
    )


@pytest.fixture(scope="session")
def doc_store():
    return DocumentStore()


@pytest.fixture(scope="session")
def retriever(doc_store):
    return RuleRetriever(doc_store)


@pytest.fixture(scope="session")
def citation_validator(doc_store):
    return CitationValidator(doc_store)


@pytest.fixture
def make_rag(doc_store, retriever, citation_validator):
    """Factory: make_rag(provider) -> RAGService. provider=None means extractive mode."""
    def _make(provider=None):
        return RAGService(doc_store=doc_store, retriever=retriever, validator=citation_validator,
                          llm_provider=provider)
    return _make


@pytest.fixture
def scripted_rag(make_rag):
    """Factory: scripted_rag(response_json) -> (RAGService, MockLLMProvider)."""
    def _make(responses=None, force_failure=False):
        provider = MockLLMProvider(responses=responses, force_failure=force_failure)
        return make_rag(provider), provider
    return _make


@pytest.fixture
def rag_service(make_rag):
    """Extractive (no-LLM) RAG service: the server default."""
    return make_rag(None)


@pytest.fixture
def client(rag_service):
    """TestClient bound to an extractive RAG service; restores app state afterwards."""
    saved = (app_context.doc_store, app_context.retriever, app_context.validator, app_context.rag_service)
    app_context.doc_store = rag_service.doc_store
    app_context.retriever = rag_service.retriever
    app_context.validator = rag_service.validator
    app_context.rag_service = rag_service
    with TestClient(app) as test_client:
        yield test_client
    (app_context.doc_store, app_context.retriever, app_context.validator, app_context.rag_service) = saved
