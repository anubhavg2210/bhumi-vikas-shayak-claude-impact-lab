"""Pydantic schemas and contracts for Bhumi Vikas Sahayak API."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfidenceLevel(str, Enum):
    """Confidence levels for evidence-grounded answers."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ChatRequest(BaseModel):
    """Incoming request to POST /api/chat."""
    model_config = ConfigDict(extra="ignore")

    question: str = Field(
        ...,
        description="User question in English or Hindi",
        min_length=1,
        max_length=2000,
        examples=["What are the building setback requirements?", "मेरा प्लॉट 200 वर्ग मीटर का है और सामने 9 मीटर चौड़ी सड़क है। आगे कितनी जगह खाली छोड़नी होगी?"]
    )
    language: Optional[str] = Field(
        default=None,
        description="'en' or 'hi'. If omitted or null, detected from the question script.",
        examples=["en", "hi"]
    )

    @field_validator("question")
    @classmethod
    def validate_question_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Question cannot be empty or whitespace only.")
        return stripped

    @field_validator("language")
    @classmethod
    def normalize_language(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        val = v.lower().strip()
        if val in ("hi", "hindi", "hi-in"):
            return "hi"
        if val in ("en", "english", "en-in", "en-us", "en-gb"):
            return "en"
        raise ValueError("Unsupported language. Use 'en' or 'hi'.")


class Citation(BaseModel):
    """Verified citation item grounded in source regulatory documents."""
    document_title: str = Field(
        ...,
        description="Verified source regulatory document title",
        examples=["Madhya Pradesh Bhumi Vikas Rules, 2012 (Consolidated up to 06-03-2025)"]
    )
    rule_number: Optional[str] = Field(
        default=None,
        description="Verified rule number (e.g., '56', '26-B'), or null if unknown",
        examples=["56", "17", "23"]
    )
    page_number: Optional[int] = Field(
        default=None,
        description="1-based PDF page number where the excerpt appears",
        examples=[77, 34, 41]
    )
    excerpt: str = Field(
        ...,
        description="Actual supporting verbatim or extracted passage from the official text"
    )


class ChatResponse(BaseModel):
    """Response contract for POST /api/chat."""
    answer: str = Field(
        ...,
        description="Evidence-grounded answer adhering strictly to regulatory text"
    )
    language: str = Field(
        ...,
        description="Language of the answer ('en' or 'hi')"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of verified citations from the rules"
    )
    confidence: ConfidenceLevel = Field(
        ...,
        description="Confidence score based on retrieval match and evidence strength"
    )
    insufficient_evidence: bool = Field(
        ...,
        description="True if regulatory collection lacks sufficient evidence or query is outside scope"
    )
    document_coverage_date: str = Field(
        ...,
        description="ISO date string of document consolidation cutoff (e.g. '2025-03-06')"
    )


class HealthResponse(BaseModel):
    """Health check response schema for GET /health."""
    status: str = Field(default="healthy", description="'healthy', or 'degraded' if no rules are loaded")
    document_coverage_date: str = Field(..., description="Regulatory consolidation cutoff date")
    documents_loaded: int = Field(..., description="Number of regulatory rules loaded into index")
    provider: str = Field(..., description="Configured LLM provider")
    version: str = Field(default="1.0.0", description="Backend service version")


class AmendmentInfo(BaseModel):
    rule_number: str
    provision: str
    date: str
    source: str
    in_collection: bool


class CoverageResponse(BaseModel):
    """Response schema for GET /api/coverage."""
    document_title: str
    document_coverage_date: str
    documents_loaded: int
    known_post_coverage_amendments: List[AmendmentInfo]
    limitations: List[str]
