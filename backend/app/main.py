"""FastAPI Application for Bhumi Vikas Sahayak."""
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app import __version__
from backend.app.config import settings
from backend.app.models.schemas import ChatRequest, ChatResponse, CoverageResponse, HealthResponse
from backend.app.services import coverage
from backend.app.services.citation_validator import CitationValidator
from backend.app.services.document_store import DocumentStore
from backend.app.services.llm_provider import get_llm_provider, provider_label
from backend.app.services.rag_service import RAGService
from backend.app.services.retriever import RuleRetriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bhumi_vikas_sahayak")


class AppContext:
    doc_store: Optional[DocumentStore] = None
    retriever: Optional[RuleRetriever] = None
    validator: Optional[CitationValidator] = None
    rag_service: Optional[RAGService] = None


app_context = AppContext()


def initialize_services() -> None:
    app_context.doc_store = DocumentStore()
    app_context.retriever = RuleRetriever(app_context.doc_store)
    app_context.validator = CitationValidator(app_context.doc_store)
    app_context.rag_service = RAGService(
        doc_store=app_context.doc_store,
        retriever=app_context.retriever,
        validator=app_context.validator,
        llm_provider=get_llm_provider(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the document index at startup (skipped if already injected, e.g. by tests)."""
    if app_context.rag_service is None:
        logger.info("Initializing document store and retriever...")
        initialize_services()
    logger.info(
        f"Ready: {len(app_context.rag_service.doc_store.get_all_rules())} rules loaded; "
        f"LLM provider: {provider_label(app_context.rag_service.llm_provider)}; "
        f"CORS origins: {settings.CORS_ORIGINS}"
    )
    yield
    logger.info("Shutting down Bhumi Vikas Sahayak backend.")


app = FastAPI(
    title="Bhumi Vikas Sahayak API",
    description="Evidence-grounded assistant for the Madhya Pradesh Bhumi Vikas Rules, 2012.",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Clean JSON response for request validation failures."""
    errors = [
        {"type": err.get("type"), "loc": list(err.get("loc", [])), "msg": err.get("msg")}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors, "message": "Invalid request parameters."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak internals (stack traces, provider messages) to clients."""
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred while processing the request.", "message": "Internal server error."},
    )


def _rules_loaded() -> int:
    store = app_context.rag_service.doc_store if app_context.rag_service else app_context.doc_store
    return len(store.get_all_rules()) if store else 0


@app.get("/", tags=["Info"])
async def root():
    return {
        "name": "Bhumi Vikas Sahayak Backend",
        "description": "Evidence-grounded QA assistant for MP Bhumi Vikas Rules 2012",
        "document_coverage_date": settings.DOCUMENT_COVERAGE_DATE,
        "docs_url": "/docs",
        "health_check": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    num_docs = _rules_loaded()
    llm = app_context.rag_service.llm_provider if app_context.rag_service else None
    provider = provider_label(llm) if app_context.rag_service else settings.LLM_PROVIDER
    # 'degraded': no rules loaded, or the configured LLM provider is missing its key/model.
    llm_ready = llm is None or llm.is_configured()
    return HealthResponse(
        status="healthy" if num_docs > 0 and llm_ready else "degraded",
        document_coverage_date=settings.DOCUMENT_COVERAGE_DATE,
        documents_loaded=num_docs,
        provider=provider,
        version=__version__,
    )


@app.get("/api/coverage", response_model=CoverageResponse, tags=["Info"])
async def coverage_info():
    """Coverage date, known post-coverage amendments, and unresolved freshness limitations."""
    return CoverageResponse(
        document_title=settings.DOCUMENT_TITLE,
        document_coverage_date=settings.DOCUMENT_COVERAGE_DATE,
        documents_loaded=_rules_loaded(),
        known_post_coverage_amendments=[a.to_dict() for a in coverage.KNOWN_POST_COVERAGE_AMENDMENTS],
        limitations=coverage.FRESHNESS_LIMITATIONS,
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """Answer a question grounded in the MP Bhumi Vikas Rules, with verified citations."""
    if app_context.rag_service is None:
        raise HTTPException(status_code=503, detail="Service is still initializing.")
    return await app_context.rag_service.answer_question(request)
