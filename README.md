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

- **Parallel Development & Mock Fallback**:
  - Reads `VITE_API_BASE_URL` to connect to `POST /api/chat`.
  - When the backend is offline or during isolated frontend development, it automatically falls back to verified MP building rules mock data.
  - Includes a UI toggle in the header to switch between Live API and Offline Mock Mode at any time.

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

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default `.env` settings:
```env
# Backend RAG API Base URL
VITE_API_BASE_URL=http://localhost:8000

# Force mock mode during offline development (true/false)
VITE_USE_MOCK=false
```

### 4. Running Locally
Start the Vite development server:
```bash
npm run dev
```
Open `http://localhost:5173/` in your browser.

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
`POST /api/chat` (or `${VITE_API_BASE_URL}/api/chat`)

### Request:
```json
{
  "question": "What are the building setback requirements for a 250 sq.m plot?",
  "language": "en"
}
```

### Expected Response:
```json
{
  "answer": "Under Rule 52 of MP Bhumi Vikas Niyam, 2012...",
  "language": "en",
  "citations": [
    {
      "document_title": "Madhya Pradesh Bhumi Vikas Niyam, 2012",
      "rule_number": "Rule 52, Table No. 13",
      "page_number": 48,
      "excerpt": "For residential plots having an area exceeding 150 sq. metres...",
      "source_url": "https://tcpm.mp.gov.in/rules/MP_Bhumi_Vikas_Niyam_2012.pdf#page=48"
    }
  ],
  "confidence": "high",
  "insufficient_evidence": false,
  "document_coverage_date": "2025-03-06"
}
```

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
