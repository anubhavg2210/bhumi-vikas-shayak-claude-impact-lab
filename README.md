# Bhumi Vikas Sahayak (भूमि विकास सहायक)

**Bhumi Vikas Sahayak** is an AI-powered regulatory assistant for understanding **Madhya Pradesh Building Regulations (Madhya Pradesh Bhumi Vikas Niyam, 2012)** and Town and Country Planning (T&CP) bylaws.

The repository is organized into modular services:

```
bhumi-vikas-shayak-claude-impact-lab/
├── backend/            # FastAPI + RAG service with Cerebras/Anthropic/OpenAI/Gemini
├── frontend/           # React 19 + Vite 8 civic regulatory user interface
├── data/               # Official MP Bhumi Vikas Niyam 2012 regulatory texts & gazettes
└── split_rules.py      # Rule ingestion and chunking script
```

---

## 🏛️ Quick Start

### 1. Frontend Setup (React + Vite)
Detailed instructions in [frontend/README.md](frontend/README.md).

```bash
cd frontend
npm install
npm run dev
```

Runs the frontend application at: `http://localhost:5173/`

### 2. Backend Setup (FastAPI + Python)
Detailed instructions in [backend/README.md](backend/README.md) and [backend/API_CONTRACT.md](backend/API_CONTRACT.md).

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m backend.app.main
```

Runs the backend API at: `http://localhost:8000` (API Docs at `http://localhost:8000/docs`).

---

## 🔌 API Integration

Frontend connects to the backend at `POST /api/chat`:
- Configured via `VITE_API_BASE_URL` in `frontend/.env` (default: `http://localhost:8000`).
- Supports automatic fallback to verified offline mock regulatory data if the backend is offline.
