"""FastAPI Application for Bhumi Vikas Sahayak."""
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app import __version__
from backend.app.config import settings
from backend.app.models.schemas import (
    ChatRequest, ChatResponse, CoverageResponse, DocumentAnalysisResponse, DocumentLimitsResponse, HealthResponse,
    normalize_language_code,
)
from backend.app.services import coverage
from backend.app.services.citation_validator import CitationValidator
from backend.app.services.document_reader import ACCEPTED_TYPES, DocumentReader, DocumentReadError, get_ocr_engine
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
        f"CORS origins: {settings.CORS_ORIGINS}; CORS regex: {settings.CORS_ORIGIN_REGEX}"
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
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
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


@app.get("/api/documents/limits", response_model=DocumentLimitsResponse, tags=["Documents"])
async def document_limits():
    """Upload limits and whether OCR (scanned PDFs, photos) is available."""
    ocr = get_ocr_engine()
    return DocumentLimitsResponse(
        max_bytes=settings.UPLOAD_MAX_BYTES,
        max_pages=settings.UPLOAD_MAX_PAGES,
        max_ocr_pages=settings.UPLOAD_MAX_OCR_PAGES,
        accepted_types=list(ACCEPTED_TYPES),
        accepted_extensions=[".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt"],
        ocr_available=ocr is not None,
        ocr_engine=ocr.name if ocr else None,
    )


@app.post("/api/documents/analyze", response_model=DocumentAnalysisResponse, tags=["Documents"])
async def analyze_document(
    file: UploadFile = File(..., description="PDF, PNG, JPEG, WebP or plain-text file"),
    question: Optional[str] = Form(default=None, description="Optional question about the document"),
    language: Optional[str] = Form(default=None, description="'en' or 'hi'; detected if omitted"),
):
    """Read an uploaded document and answer a question about it against the rules.

    The file is processed in memory and not stored or added to the rule database.
    """
    if app_context.rag_service is None:
        raise HTTPException(status_code=503, detail="Service is still initializing.")
    try:
        lang = normalize_language_code(language)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if question and len(question.strip()) > settings.MAX_QUESTION_LENGTH:
        raise HTTPException(status_code=422, detail=f"Question must be at most {settings.MAX_QUESTION_LENGTH} characters.")

    # Read at most one byte past the limit so oversized uploads are rejected without buffering them.
    data = await file.read(settings.UPLOAD_MAX_BYTES + 1)
    await file.close()
    try:
        doc = await DocumentReader().read(file.filename or "document", data)
    except DocumentReadError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    logger.info(f"Document read: {doc.media_type}, {len(doc.pages)}/{doc.pages_total} pages, "
                f"{doc.characters} chars, methods={doc.methods}")
    return await app_context.rag_service.analyze_document(doc, question, lang)


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """Answer a question grounded in the MP Bhumi Vikas Rules, with verified citations."""
    if app_context.rag_service is None:
        raise HTTPException(status_code=503, detail="Service is still initializing.")
    return await app_context.rag_service.answer_question(request)
