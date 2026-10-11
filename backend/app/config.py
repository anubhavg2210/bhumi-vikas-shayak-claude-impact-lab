"""Configuration settings for Bhumi Vikas Sahayak backend."""
import json
from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing_extensions import Annotated

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

# Shared Inference model listed in the Cerebras docs (inference-docs.cerebras.ai/models/overview,
# checked 2026-10-11) that supports strict JSON-schema output. Override with CEREBRAS_MODEL.
DEFAULT_CEREBRAS_MODEL = "gpt-oss-120b"

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
DEFAULT_CORS_ORIGIN_REGEX = r"^https:\/\/([a-zA-Z0-9-]+\.)*vercel\.app$"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `backend/.env`.

    Only `backend/.env` is read (it is git-ignored by `backend/.gitignore`), whichever
    directory the server is started from. Real environment variables take precedence.
    """
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    # Comma-separated list or JSON array. A wildcard is never added implicitly.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = list(DEFAULT_CORS_ORIGINS)
    # Regex pattern matching allowed origins (allows Vercel preview & production deployments by default).
    CORS_ORIGIN_REGEX: Optional[str] = DEFAULT_CORS_ORIGIN_REGEX

    # Legal document collection metadata
    DOCUMENT_COVERAGE_DATE: str = "2025-03-06"
    DOCUMENT_TITLE: str = "Madhya Pradesh Bhumi Vikas Rules, 2012 (Consolidated up to 06-03-2025)"
    DATA_DIR: str = "data"

    # LLM provider: 'extractive' (no LLM, quotes verified passages), 'cerebras', 'gemini', 'openai', 'anthropic'.
    # 'mock' is accepted as a legacy alias for 'extractive'.
    LLM_PROVIDER: str = "extractive"
    LLM_TIMEOUT_SECONDS: float = 60.0

    # Cerebras Cloud (OpenAI-compatible API, called through the `openai` SDK)
    CEREBRAS_API_KEY: Optional[str] = None
    CEREBRAS_MODEL: str = DEFAULT_CEREBRAS_MODEL
    CEREBRAS_BASE_URL: str = "https://api.cerebras.ai/v1"
    # Output cap; on reasoning models it includes reasoning tokens.
    CEREBRAS_MAX_COMPLETION_TOKENS: int = 4096
    # Model-dependent: gpt-oss-120b accepts low|medium|high. Empty = model default.
    CEREBRAS_REASONING_EFFORT: Optional[str] = None
    # 0-2. Empty = model default.
    CEREBRAS_TEMPERATURE: Optional[float] = None
    # Per-attempt timeout. Cerebras usually answers in ~1 s.
    CEREBRAS_TIMEOUT_SECONDS: float = 20.0
    # Retries for rate limits (429), timeouts, network and 5xx errors...
    CEREBRAS_MAX_RETRIES: int = 2
    # ...but only if the server's retry-after is at most this long; otherwise fail fast.
    # Worst case per answer: (MAX_RETRIES + 1) * TIMEOUT + MAX_RETRIES * MAX_RETRY_WAIT = 70 s,
    # below the frontend's 90 s request timeout.
    CEREBRAS_MAX_RETRY_WAIT_SECONDS: float = 5.0

    # Uploaded documents (POST /api/documents/analyze). Files are processed in memory, never stored.
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024
    UPLOAD_MAX_PAGES: int = 30          # PDF pages read
    # Scanned pages / images sent to OCR per upload. Each costs one LLM request; the Cerebras free
    # tier allows 5 requests/minute, so 3 OCR pages + 1 answer fit in one minute.
    UPLOAD_MAX_OCR_PAGES: int = 3
    UPLOAD_MAX_TEXT_CHARS: int = 24000  # document text sent to the LLM
    # OCR for photos and scanned PDFs: 'auto' (Cerebras vision when a Cerebras key is set), 'cerebras', 'none'
    OCR_ENGINE: str = "auto"
    # Image-capable Cerebras model (verified on this account 2026-10-11: qwen-3.8-27b accepts images)
    CEREBRAS_VISION_MODEL: str = "qwen-3.8-27b"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-opus-5-5"
    ANTHROPIC_EFFORT: str = "medium"
    # Server-side refusal fallback (Claude API only). Disable for Bedrock/Vertex/Foundry gateways.
    ANTHROPIC_ENABLE_FALLBACKS: bool = True

    # Retrieval configuration
    MAX_RETRIEVAL_CHUNKS: int = 8
    MIN_SIMILARITY_THRESHOLD: float = 0.15
    MAX_QUESTION_LENGTH: int = 2000

    @field_validator(
        "CEREBRAS_API_KEY", "CEREBRAS_REASONING_EFFORT", "CEREBRAS_TEMPERATURE",
        "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "CORS_ORIGIN_REGEX", mode="before",
    )
    @classmethod
    def blank_to_none(cls, v):
        """Treat `KEY=` (empty placeholder in .env) as unset."""
        if isinstance(v, str) and not v.strip():
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("CEREBRAS_MODEL", mode="before")
    @classmethod
    def default_cerebras_model(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return DEFAULT_CEREBRAS_MODEL
        return v.strip()

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str], None]) -> List[str]:
        if v is None:
            return list(DEFAULT_CORS_ORIGINS)
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                parsed = json.loads(v)
                return [str(o).strip() for o in parsed if str(o).strip()]
            return [o.strip() for o in v.split(",") if o.strip()]
        return [str(o).strip() for o in v if str(o).strip()]

    def resolve_data_path(self, filename: str = "bhumi_vikas_rules.jsonl") -> Path:
        """Find a data file across common working directory locations."""
        candidates = [
            Path(self.DATA_DIR) / filename,
            REPO_ROOT / self.DATA_DIR / filename,
            REPO_ROOT / "data" / filename,
        ]
        for p in candidates:
            if p.is_file():
                return p.resolve()
        return candidates[1].resolve()


settings = Settings()
