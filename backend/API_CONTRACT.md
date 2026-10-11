# Bhumi Vikas Sahayak: Backend API Contract

This is the REST contract for the frontend. Field names and types are stable. Changes will only add new fields, never rename or remove existing ones.

- Base URL (local dev): `http://localhost:8000`
- OpenAPI / Swagger UI: `http://localhost:8000/docs` (ReDoc at `/redoc`)
- All bodies are JSON (`Content-Type: application/json`, UTF-8). Hindi text is returned as plain UTF-8, not escaped.

## CORS

The allowed origins come from `CORS_ORIGINS` in `backend/.env`, given as a comma-separated list or a JSON array. The defaults are:

```
http://localhost:3000, http://localhost:5173, http://127.0.0.1:3000, http://127.0.0.1:5173
```

CORS allows the `GET`, `POST` and `OPTIONS` methods and the `Content-Type` and `Accept` request headers. Credentials (cookies) are not used. There is no wildcard origin, so if your dev server runs on another port, add it to `CORS_ORIGINS`.

---

## `POST /api/chat`

Ask a question in English or Hindi.

### Request

```json
{
  "question": "What is the minimum rear open space for a 150 sq m residential plot?",
  "language": "en"
}
```

| Field | Type | Required | Rules |
|---|---|---|---|
| `question` | string | yes | 1–2000 characters after trimming. Cannot be blank. |
| `language` | string or null | no | `"en"` or `"hi"` (also accepts `"english"`, `"hindi"`, `"en-IN"`, `"hi-IN"`). If omitted or null, it is detected from the script: Devanagari means `hi`, anything else means `en`. Any other value returns 422. |

Unknown extra fields are ignored.

### Response `200 OK`

Every successful response has exactly these six fields:

```json
{
  "answer": "string",
  "language": "en",
  "citations": [
    {
      "document_title": "Madhya Pradesh Bhumi Vikas Rules, 2012 (Consolidated up to 06-03-2025)",
      "rule_number": "56",
      "page_number": 78,
      "excerpt": "Above 40.00 and up to 150.00 1.50"
    }
  ],
  "confidence": "high",
  "insufficient_evidence": false,
  "document_coverage_date": "2025-03-06"
}
```

The excerpt above is a real row of the Rule 56(2)(a) table on PDF page 78.

| Field | Type | Meaning |
|---|---|---|
| `answer` | string | The answer text in `language`. It may contain `\n\n` paragraph breaks. Freshness or caution notes are appended as their own paragraph (see below). |
| `language` | `"en"` \| `"hi"` | The language the answer is written in. |
| `citations` | array | Source passages that support the answer. Every one has been checked to appear verbatim in the rules. The list is empty when `insufficient_evidence` is `true`. |
| `citations[].document_title` | string | Always the title of the consolidated rules document. It comes from the server, not from the model. |
| `citations[].rule_number` | string or **null** | The rule number as printed, e.g. `"56"` or `"26-B"`. It is a string, not a number. |
| `citations[].page_number` | integer or **null** | The 1-based page number in the PDF (`data/resources/MP_Bhumi_Vikas_Rules_2012_upto_2025-03-06_EN.pdf`). It is `null` if the page could not be confirmed. The server never guesses a page. |
| `citations[].excerpt` | string | The verbatim passage from the English consolidated text, with whitespace collapsed. Excerpts stay in English even when the answer is in Hindi. Tables are flattened, so columns become space-separated values. |
| `confidence` | `"high"` \| `"medium"` \| `"low"` | How strongly the evidence supports the answer. It is never higher than the retrieval match quality. It is capped at `medium` if some of the model's citations were rejected, and set to `low` if the answer states figures that do not appear in the cited text. |
| `insufficient_evidence` | boolean | `true` when the rules do not answer the question, the question is out of scope, or the answer could not be verified. In that case `answer` explains why and may name rules worth reading. |
| `document_coverage_date` | string (ISO date) | The date the rules were consolidated up to. Currently `"2025-03-06"`. |

#### Answer modes

The same response shape is used in every mode:

1. **LLM mode** (`LLM_PROVIDER=cerebras`, or `anthropic|openai|gemini`): the answer is generated from the retrieved passages. Citations are built from the retrieval records the model cites, and each quote is checked verbatim.
2. **Retrieval-only mode** (`LLM_PROVIDER=extractive`, the default with no API key): `answer` is a short notice ("AI summarisation is not enabled…") and `citations` holds the most relevant verified passages. The UI should present the citations as the content in this mode.
3. **LLM failure** (missing key, provider down, rate limit, timeout, refusal, or unparseable output): the API still returns `200`, with an answer starting "The AI answer service is currently unavailable…" (in Hindi: "एआई उत्तर सेवा अभी उपलब्ध नहीं है।"), `confidence: "low"`, and retrieval-only citations. Nothing is generated, and the API does not return a 5xx for provider outages.

#### Notes appended to `answer`

These are short paragraphs that the UI can render as-is:

- **Freshness note.** It starts with `Note:` in English or `सूचना:` in Hindi. It is added when the question refers to a date after the coverage date or to the "latest" rules, or when a cited rule has a known later amendment (currently Rule 2(5)(c), amended 2026-08-28; that text is not in the collection).
- **Caution.** It starts with `Caution:` in English or `सावधानी:` in Hindi. It is added when the answer contains figures that do not appear in the cited excerpts, and `confidence` is then `low`.

### Examples

Out of scope:

```json
// request
{"question": "How do I pay my property tax online?", "language": "en"}
// response
{
  "answer": "This question is outside the scope of the Madhya Pradesh Bhumi Vikas Rules, 2012. The rules govern land development and building permission and contain no provision on this topic.",
  "language": "en",
  "citations": [],
  "confidence": "low",
  "insufficient_evidence": true,
  "document_coverage_date": "2025-03-06"
}
```

A Hindi request, where the language may be omitted because the script is detected:

```json
{"question": "बिल्डिंग परमिशन की फीस कितनी है और किस नियम में लिखी है?"}
```

The response has `"language": "hi"`, the `answer` in Hindi, and English excerpts in `citations`.

### Errors

| Status | When | Body |
|---|---|---|
| `422` | Missing or blank `question`, a non-string value, more than 2000 characters, an unsupported `language`, or malformed JSON | `{"detail": [{"type": "...", "loc": ["body", "question"], "msg": "..."}], "message": "Invalid request parameters."}` |
| `405` | A method other than POST | FastAPI default |
| `503` | The service is still initialising (rare, only during startup) | `{"detail": "Service is still initializing."}` |
| `500` | An unexpected server bug | `{"detail": "An internal error occurred while processing the request.", "message": "Internal server error."}` Internal details are never included. |

---

## `GET /health`

```json
{
  "status": "healthy",
  "document_coverage_date": "2025-03-06",
  "documents_loaded": 106,
  "provider": "extractive",
  "version": "1.0.0"
}
```

`status` is `"degraded"` if no rules are loaded, or if the configured LLM provider is missing its API key. `provider` is one of `extractive`, `cerebras`, `anthropic`, `openai` or `gemini`.

## `GET /api/coverage`

This endpoint is for a "data current as of" banner or an About page.

```json
{
  "document_title": "Madhya Pradesh Bhumi Vikas Rules, 2012 (Consolidated up to 06-03-2025)",
  "document_coverage_date": "2025-03-06",
  "documents_loaded": 106,
  "known_post_coverage_amendments": [
    {"rule_number": "2", "provision": "Rule 2(5)(c)", "date": "2026-08-28", "source": "data/DATA_DICTIONARY.md", "in_collection": false}
  ],
  "limitations": ["..."]
}
```

## `GET /`

This returns basic service information and links to `/docs` and `/health`.

---

## Integration checklist for the frontend

- Show `document_coverage_date` near every answer, and preferably the `/api/coverage` limitations once per session.
- When `insufficient_evidence` is `true`, show the answer as a "not found" message, not as an answer.
- Render each citation as `Rule {rule_number}, page {page_number}`. Handle `null` for either one, e.g. by hiding the field.
- Treat `excerpt` and `answer` as plain text, never HTML.
- Send `language` from the UI language toggle, or omit it for auto-detection.
