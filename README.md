# Apollo

Apollo is a Gemini-powered medical bill auditor. Upload a bill image or PDF, extract structured line items, benchmark each charge against Medicare and CLFS pricing data, detect billing errors, surface state and federal patient protections, and generate a ready-to-send dispute letter.

## What Apollo Does

- Parses real medical bills with Gemini vision
- Benchmarks each line item against CMS Medicare and clinical lab rates
- Detects duplicates and unbundling, plus AI-audited billing issues
- Shows state-specific protections alongside federal billing laws
- Generates a patient-signed dispute letter with pricing and legal citations
- Includes a standalone CPT Price Explorer for live demos and Q&A

## Stack

- Frontend: React 19 + Vite + Tailwind CSS
- Backend: FastAPI + SQLite
- AI: Google Gemini API
- Data: CMS physician fee schedule, CLFS lab rates, CCI edits, state law dataset

## Repository Layout

```text
Apollo/
├── PRD.md
├── README.md
├── .env.example
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   ├── services/
│   ├── data/
│   └── db/
├── frontend/
│   ├── package.json
│   ├── .env.example
│   └── src/
└── scripts/
```

## Prerequisites

- Python 3.11+ with the backend dependencies installed
- Node.js 20+ and npm
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- Optional for PDF uploads: `poppler`
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`

## Environment Setup

Create a root `.env` from `.env.example`:

```bash
cp .env.example .env
```

Create a frontend env file if you need to override the API base URL:

```bash
cp frontend/.env.example frontend/.env
```

Required root env vars:

- `GEMINI_API_KEY`
- `ALLOWED_ORIGINS`
- `PORT`

Optional model tuning:

- `GEMINI_MODEL`
- `GEMINI_ANALYSIS_MODEL`
- `GEMINI_LETTER_MODEL`

## Install Dependencies

Backend:

```bash
pip install -r backend/requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

## Data and Database

The repository includes the raw CMS / CLFS / CCI / state law data under `backend/data/`.

If `backend/db/pricing.db` is missing or stale, rebuild it with:

```bash
python backend/db/seed_db.py
```

## Run Locally

Start the backend:

```bash
cd backend
python -m uvicorn main:app --host localhost --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm run dev -- --host localhost --port 5173
```

Open:

- Frontend: `http://localhost:5173`
- FastAPI docs: `http://localhost:8000/docs`

## Demo Flow

Recommended live demo:

1. Open Apollo at `http://localhost:5173`
2. Click the sample bill `ER Visit with Labs`
3. Wait for the full Gemini pipeline to complete
4. Walk judges through:
   - savings summary
   - parsed bill rows
   - price comparison visualization
   - billing error cards
   - Virginia / federal law protections
   - generated dispute letter
5. Switch to `Price Explorer` and search `MRI`

Included sample bills:

- `sample-a.png`: ER visit with duplicate + unbundled lab billing
- `sample-b.png`: overcharges without coding errors
- `sample-c.png`: comparatively clean bill

## Key API Endpoints

- `POST /api/analyze`
- `POST /api/generate-letter`
- `GET /api/lookup/{cpt_code}`
- `GET /api/search-cpt?q=...`
- `GET /api/state-laws/{state_code}`

Example checks:

```bash
curl http://localhost:8000/api/lookup/99214
curl "http://localhost:8000/api/search-cpt?q=MRI"
curl http://localhost:8000/api/state-laws/VA
```

## Current Notes

- The full `POST /api/analyze` path is entirely live Gemini-backed. There is no demo-only mock pipeline.
- PDF export is generated client-side from the current letter.
- The regenerate flow lets the user choose which pricing issues and billing errors to include, then regenerate the letter with edited draft guidance.

## Troubleshooting

- `GEMINI_API_KEY environment variable is required`
  - Add the key to the root `.env`
- `No module named uvicorn`
  - Install backend dependencies in the Python environment you are actually using
- `POST /api/analyze` fails on PDFs
  - Install `poppler`
- Missing DB rows / lookup failures
  - Re-run `python backend/db/seed_db.py`

## Submission Checklist

- Frontend runs locally
- Backend runs locally
- Sample bill A completes end-to-end
- `GET /api/lookup/99214` returns a Medicare rate
- `GET /api/lookup/80053` returns a non-zero lab rate
- `GET /api/search-cpt?q=MRI` returns results
- `GET /api/state-laws/VA` returns Virginia laws

