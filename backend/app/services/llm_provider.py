"""Configurable LLM provider integrations (Cerebras, Gemini, OpenAI-compatible, Anthropic) plus a test mock.

Providers only turn (system_prompt, user_prompt) into raw text. Grounding, JSON parsing and
citation validation happen in RAGService, so no provider output is trusted as-is.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Sequence, Union
import httpx
from backend.app.config import settings

logger = logging.getLogger(__name__)

EXTRACTIVE_PROVIDER_NAMES = {"extractive", "none", "mock"}


class LLMProviderError(Exception):
    """Raised when an LLM provider encounters an API, network, refusal, or configuration error.

    `reason` is a stable machine-readable code (e.g. 'auth', 'rate_limited', 'timeout').
    Messages never contain API keys.
    """

    def __init__(self, message: str, reason: str = "provider_error"):
        super().__init__(message)
        self.reason = reason


class LLMConfigurationError(ValueError):
    """Raised at startup when LLM_PROVIDER is set to an unknown value."""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str = "base"

    @abstractmethod
    async def generate_response(self, system_prompt: str, user_prompt: str,
                                json_schema: Optional[dict] = None) -> str:
        """Generate a response. `json_schema` is a hint providers may use to constrain output."""

    def is_configured(self) -> bool:
        """False when required settings (e.g. an API key) are missing."""
        return True


class MockLLMProvider(LLMProvider):
    """Scripted provider for deterministic tests. It contains no legal content of its own.

    - `responses`: a string returned every call, or a list consumed in order.
    - `force_failure`: raise LLMProviderError on every call.
    Every call is recorded in `calls` so tests can inspect the prompts that were sent.
    """

    name = "mock"

    def __init__(
        self,
        responses: Union[str, Sequence[str], None] = None,
        force_failure: bool = False,
        deterministic_response: Optional[str] = None,
    ):
        if deterministic_response is not None and responses is None:
            responses = deterministic_response
        self._responses = responses
        self._index = 0
        self.force_failure = force_failure
        self.calls: List[dict] = []

    async def generate_response(self, system_prompt: str, user_prompt: str,
                                json_schema: Optional[dict] = None) -> str:
        self.calls.append({"system": system_prompt, "user": user_prompt, "json_schema": json_schema})
        if self.force_failure:
            raise LLMProviderError("Simulated LLM provider failure.")
        if self._responses is None:
            raise LLMProviderError("MockLLMProvider has no scripted response.")
        if isinstance(self._responses, str):
            return self._responses
        if self._index >= len(self._responses):
            raise LLMProviderError("MockLLMProvider ran out of scripted responses.")
        out = self._responses[self._index]
        self._index += 1
        return out


def _short(body: str, limit: int = 300) -> str:
    return body if len(body) <= limit else body[:limit] + "..."


class GeminiLLMProvider(LLMProvider):
    """Google Gemini generateContent REST API."""

    name = "gemini"

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None,
                 transport: Optional[httpx.AsyncBaseTransport] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self._transport = transport

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate_response(self, system_prompt: str, user_prompt: str,
                                json_schema: Optional[dict] = None) -> str:
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured.", reason="not_configured")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        # Key goes in a header, not the URL, so it does not end up in access logs.
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"},
        }
        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS, transport=self._transport) as client:
                res = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as e:
            raise LLMProviderError(f"Network error communicating with Gemini: {type(e).__name__}") from e
        if res.status_code != 200:
            raise LLMProviderError(f"Gemini API returned HTTP {res.status_code}: {_short(res.text)}")
        try:
            data = res.json()
            candidate = data["candidates"][0]
            if candidate.get("finishReason") not in (None, "STOP", "MAX_TOKENS"):
                raise LLMProviderError(f"Gemini stopped with finishReason={candidate.get('finishReason')}")
            return "".join(p.get("text", "") for p in candidate["content"]["parts"])
        except LLMProviderError:
            raise
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise LLMProviderError(f"Unexpected Gemini response shape: {type(e).__name__}") from e


class OpenAILLMProvider(LLMProvider):
    """OpenAI or OpenAI-compatible chat completions API."""

    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 base_url: Optional[str] = None, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self._transport = transport

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate_response(self, system_prompt: str, user_prompt: str,
                                json_schema: Optional[dict] = None) -> str:
        if not self.api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured.", reason="not_configured")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS, transport=self._transport) as client:
                res = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
        except httpx.HTTPError as e:
            raise LLMProviderError(f"Network error communicating with OpenAI: {type(e).__name__}") from e
        if res.status_code != 200:
            raise LLMProviderError(f"OpenAI API returned HTTP {res.status_code}: {_short(res.text)}")
        try:
            content = res.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise LLMProviderError(f"Unexpected OpenAI response shape: {type(e).__name__}") from e
        if not content:
            raise LLMProviderError("OpenAI returned an empty message (possibly a refusal).")
        return content


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude via the official `anthropic` SDK (Messages API).

    Claude Opus 5.5 rejects sampling parameters (temperature/top_p) and thinking cannot be
    disabled; output depth is controlled with `output_config.effort` instead.
    """

    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, client: Any = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise LLMProviderError("The 'anthropic' package is not installed (pip install anthropic).") from e
            # With no explicit key the SDK resolves credentials from the environment.
            kwargs = {"timeout": settings.LLM_TIMEOUT_SECONDS, "max_retries": 2}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    async def generate_response(self, system_prompt: str, user_prompt: str,
                                json_schema: Optional[dict] = None) -> str:
        client = self._get_client()
        request = dict(
            model=self.model,
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_config={"effort": settings.ANTHROPIC_EFFORT},
        )
        try:
            if settings.ANTHROPIC_ENABLE_FALLBACKS:
                # Server-side refusal fallback: on a policy decline the API re-runs the request
                # on a fallback model inside the same call.
                response = await client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request
                )
            else:
                response = await client.messages.create(**request)
        except Exception as e:  # anthropic.APIError subclasses, timeouts, connection errors
            raise LLMProviderError(f"Anthropic request failed: {type(e).__name__}") from e

        if getattr(response, "stop_reason", None) == "refusal":
            raise LLMProviderError("Anthropic model declined the request (stop_reason=refusal).")
        text = "".join(
            getattr(block, "text", "") for block in (response.content or []) if getattr(block, "type", None) == "text"
        )
        if not text.strip():
            raise LLMProviderError(f"Anthropic returned no text (stop_reason={getattr(response, 'stop_reason', None)}).")
        return text


class CerebrasLLMProvider(LLMProvider):
    """Cerebras Cloud via the `openai` SDK pointed at Cerebras' OpenAI-compatible endpoint.

    Docs: https://inference-docs.cerebras.ai/resources/openai
    - Structured output uses `response_format={"type": "json_schema", ..., "strict": True}`
      (supported by gpt-oss-120b and qwen-3.8-27b on Shared Inference).
    - Reasoning text is returned in `message.reasoning`, separate from `message.content`;
      `max_completion_tokens` includes reasoning tokens.
    - The SDK retries connection errors, 408, 429 and 5xx (`CEREBRAS_MAX_RETRIES`).
    """

    name = "cerebras"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 base_url: Optional[str] = None, client: Any = None, http_client: Any = None):
        self.api_key = api_key if api_key is not None else settings.CEREBRAS_API_KEY
        self.model = model or settings.CEREBRAS_MODEL
        self.base_url = (base_url or settings.CEREBRAS_BASE_URL).rstrip("/")
        self._client = client
        self._http_client = http_client  # tests inject an httpx2 client with a mock transport

    def is_configured(self) -> bool:
        return bool(self.api_key) and bool(self.model)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        # Check before building the client: with api_key=None the openai SDK would silently
        # fall back to the OPENAI_API_KEY environment variable.
        if not self.api_key:
            raise LLMProviderError("CEREBRAS_API_KEY is not set.", reason="not_configured")
        try:
            import openai
        except ImportError:
            raise LLMProviderError("The 'openai' package is not installed (pip install openai).",
                                   reason="not_configured") from None
        kwargs = dict(api_key=self.api_key, base_url=self.base_url,
                      timeout=settings.LLM_TIMEOUT_SECONDS, max_retries=settings.CEREBRAS_MAX_RETRIES)
        if self._http_client is not None:
            kwargs["http_client"] = self._http_client
        self._client = openai.AsyncOpenAI(**kwargs)
        return self._client

    def _build_request(self, system_prompt: str, user_prompt: str, json_schema: Optional[dict]) -> dict:
        request = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=settings.CEREBRAS_MAX_COMPLETION_TOKENS,
            stream=False,
        )
        if json_schema:
            request["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "grounded_answer", "strict": True, "schema": json_schema},
            }
        else:
            request["response_format"] = {"type": "json_object"}
        if settings.CEREBRAS_REASONING_EFFORT:
            request["reasoning_effort"] = settings.CEREBRAS_REASONING_EFFORT
        if settings.CEREBRAS_TEMPERATURE is not None:
            request["temperature"] = settings.CEREBRAS_TEMPERATURE
        return request

    @staticmethod
    def _error_code(exc: Any) -> str:
        """Provider error code from the response body (e.g. 'model_not_found'); never the message text."""
        body = getattr(exc, "body", None)
        code = None
        if isinstance(body, dict):
            nested = body.get("error")
            code = body.get("code") or (nested.get("code") if isinstance(nested, dict) else None)
        if isinstance(code, str) and code.replace("_", "").isalnum() and len(code) < 64:
            return f", code={code}"
        return ""

    def _translate_error(self, exc: Exception) -> LLMProviderError:
        import openai

        status = getattr(exc, "status_code", None)
        request_id = getattr(exc, "request_id", None)
        suffix = self._error_code(exc) + (f", request_id={request_id}" if request_id else "")
        if isinstance(exc, openai.AuthenticationError):
            return LLMProviderError(f"Cerebras rejected the API key (HTTP 401{suffix}). Check CEREBRAS_API_KEY.", "auth")
        if isinstance(exc, openai.PermissionDeniedError):
            return LLMProviderError(f"Cerebras denied access (HTTP 403{suffix}). The key may not have access to "
                                    f"model '{self.model}'.", "auth")
        if isinstance(exc, openai.NotFoundError):
            return LLMProviderError(f"Cerebras model '{self.model}' was not found (HTTP 404{suffix}). "
                                    "Check CEREBRAS_MODEL against the models your account can use.", "model_not_found")
        if isinstance(exc, openai.RateLimitError):
            return LLMProviderError(f"Cerebras rate limit or quota exceeded (HTTP 429{suffix}).", "rate_limited")
        if isinstance(exc, (openai.BadRequestError, openai.UnprocessableEntityError)):
            return LLMProviderError(f"Cerebras rejected the request (HTTP {status}{suffix}). The model may not "
                                    "support a configured parameter (response_format, reasoning_effort, temperature) "
                                    "or the model ID is invalid.", "bad_request")
        if isinstance(exc, openai.APITimeoutError):
            return LLMProviderError(f"Cerebras request timed out after {settings.LLM_TIMEOUT_SECONDS:g}s "
                                    f"(including {settings.CEREBRAS_MAX_RETRIES} retries).", "timeout")
        if isinstance(exc, openai.APIConnectionError):
            return LLMProviderError("Could not connect to Cerebras (network error).", "network")
        if isinstance(exc, openai.APIStatusError):
            if status == 402:
                return LLMProviderError(f"Cerebras reports a billing/payment problem (HTTP 402{suffix}).", "billing")
            reason = "server_error" if status and status >= 500 else "http_error"
            return LLMProviderError(f"Cerebras returned HTTP {status}{suffix}.", reason)
        return LLMProviderError(f"Cerebras request failed: {type(exc).__name__}", "provider_error")

    async def generate_response(self, system_prompt: str, user_prompt: str,
                                json_schema: Optional[dict] = None) -> str:
        client = self._get_client()
        request = self._build_request(system_prompt, user_prompt, json_schema)
        started = time.monotonic()
        try:
            completion = await client.chat.completions.create(**request)
        except Exception as e:
            # `from None`: the SDK exception text is not chained into logs or responses.
            raise self._translate_error(e) from None

        try:
            choice = completion.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            content = choice.message.content
        except (AttributeError, IndexError, TypeError):
            raise LLMProviderError("Unexpected Cerebras response shape.", "bad_response") from None

        usage = getattr(completion, "usage", None)
        logger.info(
            f"Cerebras {self.model}: finish_reason={finish_reason}, "
            f"completion_tokens={getattr(usage, 'completion_tokens', '?')}, "
            f"latency={time.monotonic() - started:.2f}s"
        )
        if finish_reason == "length":
            raise LLMProviderError("Cerebras output was truncated (finish_reason=length). "
                                   "Increase CEREBRAS_MAX_COMPLETION_TOKENS or lower CEREBRAS_REASONING_EFFORT.",
                                   "truncated")
        if finish_reason == "content_filter":
            raise LLMProviderError("Cerebras withheld the response (finish_reason=content_filter).", "refusal")
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("Cerebras returned an empty message.", "bad_response")
        return content


def get_llm_provider(provider_type: Optional[str] = None) -> Optional[LLMProvider]:
    """Return the configured provider, or None for extractive (retrieval-only) mode."""
    p_type = (provider_type or settings.LLM_PROVIDER or "extractive").lower().strip()
    if p_type in EXTRACTIVE_PROVIDER_NAMES:
        if p_type == "mock":
            logger.info("LLM_PROVIDER=mock is treated as 'extractive' (retrieval-only answers).")
        return None
    if p_type == "cerebras":
        provider = CerebrasLLMProvider()
        if not provider.is_configured():
            logger.warning("LLM_PROVIDER=cerebras but CEREBRAS_API_KEY is not set; chat answers will report "
                           "the AI service as unavailable until it is configured.")
        return provider
    if p_type == "gemini":
        return GeminiLLMProvider()
    if p_type in ("openai", "chatgpt"):
        return OpenAILLMProvider()
    if p_type in ("anthropic", "claude"):
        return AnthropicLLMProvider()
    raise LLMConfigurationError(
        f"Unknown LLM_PROVIDER '{p_type}'. Use one of: extractive, cerebras, gemini, openai, anthropic."
    )


def provider_label(provider: Optional[LLMProvider]) -> str:
    return provider.name if provider else "extractive"
