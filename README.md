# Bhumi Vikas Sahayak (भूमि विकास सहायक) — Frontend

Bhumi Vikas Sahayak is an AI-powered regulatory assistant designed to help citizens, planners, architects, and municipal officials understand and navigate **Madhya Pradesh Building Regulations (Madhya Pradesh Bhumi Vikas Niyam, 2012)** and Town and Country Planning (T&CP) bylaws.

This frontend application delivers an accessible civic-technology interface with verifiable statutory citations, bilingual support (English & हिन्दी), and graceful degradation.

---

## 🏛️ Key Features

- **Dashboard**:
  - Civic branding and Directorate of Town & Country Planning (T&CP) regulatory theme.
  - Statutory scope and legal coverage notice (MP Bhumi Vikas Niyam, 2012 & amended gazette schedules).
  - Main natural language question input with multiline expansion and keyboard shortcuts (`Enter` to submit, `Shift+Enter` for newline).
  - Categorized example prompt cards (Setbacks, FAR/FSI, Building Permissions, Parking Standards).
  - Real-time bilingual switch (**English** / **हिन्दी**).
  
- **AI Consultation Chat**:
  - Clear visual separation between AI statutory analysis and cited legal evidence.
  - Multi-step loading feedback ("Analyzing query against MP Bhumi Vikas Niyam...", "Retrieving rule provisions...", "Verifying citations...").
  - Confidence scoring badges (`High`, `Medium`, `Low`, `Insufficient Evidence`).
  - Input validation preventing empty submissions or duplicate requests while queries are in-flight.
  - Error detection with one-click retry functionality.

- **Verifiable Citation Cards**:
  - Source document title.
  - Specific Rule / Schedule number (e.g. *Rule 52: Marginal Open Spaces*, *Rule 60: FAR*).
  - Official gazette page number.
  - Supporting legal excerpts with statutory quote styling.
  - Interactive **Passage Inspector Modal** with one-click clipboard copying and external PDF links.

- **Insufficient Evidence Safeguard**:
  - When backend cannot find verified regulatory texts (`insufficient_evidence: true`), displays a clear non-hallucination notice.
  - Explains why evidence was not found (e.g., local Master Plan variance, out-of-scope domain such as agricultural subsidies or crypto).
  - Recommends official next steps and links to the MP Town and Country Planning Directorate.

- **Backend connection & Mock Mode**:
  - In development, calls go to same-origin `POST /api/chat` and `GET /health`, which the Vite dev server proxies to the FastAPI backend (`BACKEND_URL`, default `http://127.0.0.1:8000`).
  - If the backend is unreachable, the chat shows a connection error with **Retry**. It never substitutes mock data on its own.
  - A header toggle switches to **Mock Mode** for offline UI work. Mock answers are sample content, not verified rule text, and each one carries a "Demo data" warning.

- **Document upload**:
  - The paperclip button in either input box (**Attach document**) accepts a PDF, PNG, JPEG, WebP photo or `.txt` file of up to 10 MB. You can send it with or without a question.
  - The file is posted to `POST /api/documents/analyze`. The backend reads it in memory (using OCR for scans and photos), does not store it, and answers against the rules with verified citations.
  - The answer shows a **Document read** card: file name, pages read, how the pages were read, any warnings, and quotes from your document that were verified against the extracted text. If AI-based OCR was used, the card warns that figures may be misread.
  - A privacy note appears while a file is attached: the document's text is sent to the AI service. Document analysis needs the Live API and is not available in Mock Mode.

---

## ⚙️ Tech Stack

- **Framework**: React 19 + Vite 8
- **Styling**: Vanilla CSS Design System with custom properties (`src/index.css`, `src/App.css`)
- **Icons**: Lucide React
- **Typography**: Inter, Outfit, Noto Sans Devanagari, JetBrains Mono
- **Testing**: Vitest + JSDOM + @testing-library/react

---

## 🚀 Getting Started

### 1. Prerequisites
- Node.js (v18+)
- npm (v9+)

### 2. Installation
```bash
npm install
```

### 3. Environment Configuration (optional)
The defaults work as-is. To change them, copy `.env.example` to `.env.local`, which is git-ignored:
```env
VITE_API_BASE_URL=            # empty in dev = use the Vite proxy
BACKEND_URL=http://127.0.0.1:8000
VITE_USE_MOCK=false
VITE_API_TIMEOUT_MS=90000
```
Only `VITE_*` variables reach the browser. **Never put API keys in frontend env files.** The Cerebras key and other backend settings live in `backend/.env` (see `backend/README.md`).

### 4. Running Locally
Start the backend and the frontend in two terminals, both from the repository root:
```bash
# terminal 1: backend API on :8000
python -m uvicorn backend.app.main:app --reload --port 8000

# terminal 2: frontend on :5173 (proxies /api and /health to :8000)
npm run dev
```
Open `http://localhost:5173/` in your browser. The header shows **Backend API Connected** when Live API mode is on.

### 5. Running Tests
Run all unit and integration tests:
```bash
npm test
```

### 6. Production Build
Build optimized production bundle:
```bash
npm run build
```

---

## 🔌 API Integration Contract

The frontend connects to the backend at:
`POST /api/chat` (or `${VITE_API_BASE_URL}/api/chat`). The authoritative contract is [`backend/API_CONTRACT.md`](backend/API_CONTRACT.md).

### Request:
```json
{
  "question": "What is the minimum rear open space for a 150 sq m residential plot?",
  "language": "en"
}
```

### Response (real backend output; excerpt shortened):
```json
{
  "answer": "...",
  "language": "en",
  "citations": [
    {
      "document_title": "Madhya Pradesh Bhumi Vikas Rules, 2012 (Consolidated up to 06-03-2025)",
      "rule_number": "56",
      "page_number": 78,
      "excerpt": "(2) Rear Open Space,- (a) Every Residential Building, having height up to 12.5 meters, shall have a Rear Open Space, as below:- ... Above 40.00 and up to 150.00 1.50 ..."
    }
  ],
  "confidence": "medium",
  "insufficient_evidence": false,
  "document_coverage_date": "2025-03-06"
}
```

`rule_number` is the bare printed number (shown as "Rule 56" / "नियम 56") and may be `null`, as may `page_number`. The backend does not send `source_url`.

---

## 📁 Project Structure

```
├── .env.example                       # Environment template
├── public/
│   └── emblem.svg                     # Civic crest SVG for MP Bhumi Vikas
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── Header.jsx                 # Branding, language switcher, mock/live toggle
│   │   ├── RegulatoryNoticeBanner.jsx # Statutory scope & legal disclaimer
│   │   ├── DashboardHero.jsx          # Civic intro, metrics, main search textarea
│   │   ├── ExamplePrompts.jsx         # Categorized MP bylaws prompt cards
│   │   ├── ChatContainer.jsx          # Chat stream, loading steps, error states
│   │   ├── ChatMessage.jsx            # Message renderer with confidence & disclaimers
│   │   ├── CitationCard.jsx           # Legal citation cards with rule & page badges
│   │   ├── CitationViewerModal.jsx    # Passage viewer dialog with copy utility
│   │   ├── InsufficientEvidenceAlert.jsx # Evidence-absent warning and guidance
│   │   └── ChatInput.jsx              # Bottom sticky input with Enter/Shift+Enter
│   ├── i18n/
│   │   └── translations.js            # Bilingual English & Hindi dictionaries
│   ├── services/
│   │   ├── chatApi.js                 # API service with timeout, retry, & fallback
│   │   └── mockData.js                # Realistic MP Bhumi Vikas Niyam mock data
│   ├── __tests__/
│   │   ├── chatApi.test.js            # API client and schema tests
│   │   └── App.test.jsx               # Integration tests for dashboard and chat
│   ├── App.css                        # App layout, responsive queries, and animations
│   ├── App.jsx                        # Application root state & view orchestrator
│   ├── index.css                      # Design system tokens and base styles
│   └── main.jsx                       # React entry point
└── vite.config.js                     # Vite and Vitest configuration
```
