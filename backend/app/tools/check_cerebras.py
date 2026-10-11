"""Check the Cerebras configuration against the live API.

Usage (from the repository root):
    python -m backend.app.tools.check_cerebras          # key, model list, configured model
    python -m backend.app.tools.check_cerebras --chat   # also one structured-output request

Never prints the API key. Exit code 0 when every check passes.
"""
import argparse
import asyncio
import json
import sys
from backend.app.config import settings
from backend.app.services.llm_provider import CerebrasLLMProvider, LLMProviderError
from backend.app.services.rag_service import ANSWER_JSON_SCHEMA


def _ok(msg: str) -> None:
    print(f"[ok]   {msg}")


def _fail(msg: str) -> None:
    print(f"[fail] {msg}")


async def run(chat: bool) -> int:
    provider = CerebrasLLMProvider()
    print(f"LLM_PROVIDER      = {settings.LLM_PROVIDER}")
    print(f"CEREBRAS_BASE_URL = {provider.base_url}")
    print(f"CEREBRAS_MODEL    = {provider.model}")
    print(f"CEREBRAS_API_KEY  = {'set' if provider.api_key else 'NOT SET'}")
    if settings.LLM_PROVIDER.lower().strip() != "cerebras":
        print("note: LLM_PROVIDER is not 'cerebras', so the server will not use Cerebras.")
    if not provider.api_key:
        _fail("CEREBRAS_API_KEY is not set (backend/.env or environment).")
        return 1

    failures = 0
    try:
        client = provider._get_client()
        page = await client.models.list()
        model_ids = sorted(m.id for m in page.data)
        _ok(f"API key accepted; models available to this key: {', '.join(model_ids) or '(none)'}")
        if provider.model in model_ids:
            _ok(f"configured model '{provider.model}' is available")
        else:
            failures += 1
            _fail(f"configured model '{provider.model}' is not in the list; set CEREBRAS_MODEL to one of the above")
    except LLMProviderError as e:
        _fail(str(e))
        return 1
    except Exception as e:  # SDK errors -> same classification the server uses
        _fail(str(provider._translate_error(e)))
        return 1

    if chat:
        try:
            raw = await provider.generate_response(
                "Reply with JSON only.",
                'Return {"answer": "ok", "confidence": "high", "insufficient_evidence": false, "citations": []}',
                json_schema=ANSWER_JSON_SCHEMA,
            )
            json.loads(raw)
            _ok("structured-output chat request succeeded")
        except LLMProviderError as e:
            failures += 1
            _fail(f"chat request failed ({e.reason}): {e}")
        except ValueError:
            failures += 1
            _fail("chat request returned non-JSON content")
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chat", action="store_true", help="also send one small structured-output request")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.chat)))


if __name__ == "__main__":
    main()
