# Apollo — Product Requirements Document

## Table of Contents
1. [Product Overview](#product-overview)
2. [System Architecture](#system-architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Data Layer — Pricing Database](#data-layer)
6. [Backend API](#backend-api)
7. [Component 1: Bill Parsing Engine](#component-1-bill-parsing-engine)
8. [Component 2: Fair Price Benchmarking](#component-2-fair-price-benchmarking)
9. [Component 3: Billing Error Detection](#component-3-billing-error-detection)
10. [Component 4: Dispute Letter Generator](#component-4-dispute-letter-generator)
11. [Component 5: Frontend Application](#component-5-frontend-application)
12. [Component 6: State Law Engine](#component-6-state-law-engine)
13. [Component 7: CPT Code Explorer](#component-7-cpt-code-explorer)
14. [Sample Data & Demo Bills](#sample-data--demo-bills)
15. [Environment Variables & Configuration](#environment-variables--configuration)
16. [Pydantic Models](#pydantic-models)
17. [Build Timeline](#build-timeline)
18. [Demo Script](#demo-script)
19. [Bonus Features](#bonus-features)

---

## Product Overview

**Apollo** is a web application that analyzes medical bills to find overcharges and billing errors. A user uploads a photo or PDF of their medical bill. Apollo parses every line item, benchmarks each charge against CMS Medicare fair pricing data, detects common billing errors (duplicates, upcoding, unbundling), calculates total potential savings, and generates a ready-to-send dispute letter with regulatory citations.

**Hackathon context**: Built for HooHacks 2026 at UVA. Competing in the **AI & Data Science** track ($1,500 prize, co-sponsored by ML@UVA) and the **Best Use of Gemini API** prize track.

**Why this wins**:
- All AI calls go through **Google Gemini API** (vision, reasoning, generation) — qualifies for the Gemini prize
- Real government pricing data (CMS Medicare Fee Schedule) grounds the AI analysis in facts — strong data science angle
- Solves a universal, painful, real-world problem — every judge has gotten a confusing medical bill
- Demo produces a specific dollar amount of savings — emotionally resonant and memorable

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Vite)                      │
│                                                                    │
│  ┌────────────┐   ┌─────────────────┐   ┌──────────────────────┐ │
│  │   Upload    │ → │    Results       │ → │   Dispute Letter     │ │
│  │   Screen    │   │    Dashboard     │   │   Preview/Download   │ │
│  └────────────┘   └─────────────────┘   └──────────────────────┘ │
│                    ┌─────────────────┐                            │
│                    │  CPT Code       │  ← Standalone search tool  │
│                    │  Explorer       │                            │
│                    └─────────────────┘                            │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP REST (JSON)
┌───────────────────────────▼──────────────────────────────────────┐
│                      BACKEND (FastAPI)                             │
│                                                                    │
│  ┌────────────────┐  ┌──────────────────────┐                    │
│  │  POST /analyze  │  │ GET /search-cpt      │                    │
│  └───────┬────────┘  │ GET /lookup/{cpt}     │                    │
│          │           └──────────┬───────────┘                    │
│          ▼                      │                                  │
│  ┌────────────────┐   ┌────────▼─────────┐   ┌────────────────┐ │
│  │  Bill Parser    │ → │  Benchmarking    │ → │ Error Detector │ │
│  │  (Gemini Vision)│   │  Engine          │   │ (Rules+Gemini) │ │
│  └────────────────┘   └───────┬──────────┘   └───────┬────────┘ │
│                               │                       │           │
│                        ┌──────▼───────┐               │           │
│                        │  SQLite DB   │               │           │
│                        │  (CMS Data + │               │           │
│                        │  State Laws) │               │           │
│                        └──────────────┘               │           │
│                                                       ▼           │
│                                          ┌──────────────────────┐│
│                                          │  Letter Generator    ││
│                                          │  (Gemini + State Law ││
│                                          │   Citations)         ││
│                                          └──────────────────────┘│
└───────────────────────────────────────────────────────────────────┘
```

**Data flow**: Upload → Parse (Gemini Vision) → Benchmark (SQLite lookups) → Detect Errors (Rules + Gemini reasoning) → Look Up State Laws (SQLite) → Generate Letter (Gemini, with state-specific citations) → Return full analysis JSON → Render dashboard

---

## Tech Stack

| Layer | Technology | Version / Notes |
|-------|-----------|-----------------|
| Frontend | React | 18+ with Vite for bundling |
| Styling | Tailwind CSS | Utility-first, fast to iterate |
| Charts | Recharts | React-native charting, good for bar/comparison charts |
| Backend | FastAPI | Python 3.11+, async support |
| AI | Google Gemini API | `gemini-2.5-pro-preview-05-06` for all AI calls |
| AI SDK | `google-genai` | Official Google Gen AI Python SDK |
| Database | SQLite | Zero-config, file-based, ships with Python |
| DB Access | `sqlite3` (stdlib) + `pandas` for initial data loading |
| PDF Handling | `pdf2image` + `Pillow` | Convert PDF pages to images for Gemini Vision |
| Deployment | Vercel (frontend) + Railway or Render (backend) | Free tiers |
| Package Manager | npm (frontend), pip (backend) |

---

## Project Structure

```
apollo/
├── README.md
├── PRD.md                          # This document
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   ├── public/
│   │   ├── apollo-logo.svg
│   │   └── sample-bills/           # Sample bill images for "Try a demo" button
│   │       ├── sample-a.png        # Bill with duplicate + overpriced lab
│   │       ├── sample-b.png        # Bill with unbundling issues
│   │       └── sample-c.png        # Clean bill (passes all checks)
│   └── src/
│       ├── main.jsx                # Entry point
│       ├── App.jsx                 # Router and layout
│       ├── api/
│       │   └── client.js           # Axios/fetch wrapper for backend calls
│       ├── components/
│       │   ├── UploadScreen.jsx    # Drag-and-drop file upload + sample bill buttons
│       │   ├── LoadingScreen.jsx   # Animated loading state during analysis
│       │   ├── ResultsDashboard.jsx # Main results container
│       │   ├── BillSummary.jsx     # Parsed line items table
│       │   ├── PriceComparison.jsx # Horizontal bar chart comparing charges vs fair prices
│       │   ├── ErrorPanel.jsx      # Detected billing errors with confidence scores
│       │   ├── SavingsSummary.jsx  # Big savings number + breakdown
│       │   ├── StateLawPanel.jsx   # State-specific protections and rights
│       │   ├── DisputeLetter.jsx   # Letter preview + download/copy buttons
│       │   └── CptExplorer.jsx     # Search any procedure → see fair price instantly
│       ├── hooks/
│       │   └── useAnalysis.js      # Custom hook managing upload → analysis → results state
│       └── utils/
│           └── formatters.js       # Currency formatting, severity colors, etc.
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                     # FastAPI app entry point, CORS config, route registration
│   ├── config.py                   # Environment variables, Gemini API key, DB path
│   ├── routers/
│   │   ├── analyze.py              # POST /analyze, POST /generate-letter, GET /lookup/{cpt}
│   │   └── explore.py              # GET /search-cpt, GET /state-laws/{state}
│   ├── services/
│   │   ├── bill_parser.py          # Gemini Vision bill parsing
│   │   ├── benchmarker.py          # Fair price benchmarking against CMS data
│   │   ├── error_detector.py       # Rule-based + AI error detection
│   │   ├── state_laws.py           # State-specific billing law lookups
│   │   └── letter_generator.py     # Dispute letter generation via Gemini (with state law citations)
│   ├── models/
│   │   └── schemas.py              # Pydantic models for all data structures
│   ├── db/
│   │   ├── pricing.db              # Pre-built SQLite database (committed to repo)
│   │   ├── seed_db.py              # Script to rebuild DB from CMS CSV files
│   │   └── cci_edits.py            # Unbundling rules lookup
│   └── data/
│       ├── cms_fee_schedule.csv    # CMS Medicare Physician Fee Schedule (national)
│       ├── cci_edits.csv           # CMS Correct Coding Initiative edits (simplified)
│       └── state_laws.json         # State-by-state billing protection laws
│
└── scripts/
    ├── generate_sample_bills.py    # Generate realistic sample bill images for demo
    └── test_gemini.py              # Quick sanity check that Gemini API key works
```

### `backend/requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
python-dotenv==1.0.1
google-genai==1.14.0
pandas==2.2.2
Pillow==10.4.0
pdf2image==1.17.0
```

Note: `pdf2image` requires the `poppler-utils` system package. Install it via `apt-get install poppler-utils` (Linux/WSL), `brew install poppler` (macOS), or download the Windows binaries from https://github.com/ossamamehmood/Poppler-windows/releases.

### `backend/config.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required. Get one at https://aistudio.google.com/apikey")

DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "db", "pricing.db"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
PORT = int(os.getenv("PORT", "8000"))
```

All services should import from this file: `from config import GEMINI_API_KEY, DATABASE_PATH`.

### Data Files — Manual Setup Required

The following files must be downloaded manually before running the seed script. **A coding agent cannot download these — the developer must do it.**

1. **`backend/data/cms_fee_schedule.csv`** — Download from https://www.cms.gov/medicare/payment/fee-schedules/physician/look-up-tool → click "National Payment Amount File" → download the CSV for the current year. The file is typically named something like `PFREVL_2026.csv`. Rename it to `cms_fee_schedule.csv` and place it in `backend/data/`.

2. **`backend/data/cci_edits.csv`** — Download from https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-edits → look for the "Practitioner PTP" edits file. This is an Excel file; export the first sheet to CSV with columns `column1_code, column2_code, effective_date, deletion_date, modifier_indicator`. Rename to `cci_edits.csv` and place in `backend/data/`.

3. **`backend/data/state_laws.json`** — This file is hand-curated and should be created from the JSON structure defined in Component 6 of this document (search for "State Law Engine" → "Data Source"). Copy the full JSON array from that section into `backend/data/state_laws.json`.

After placing all three files, run: `cd backend && python db/seed_db.py`

---

## Data Layer

### CMS Medicare Physician Fee Schedule

This is the core pricing reference. It's a free, public dataset from the Centers for Medicare & Medicaid Services containing the Medicare-allowed payment for every medical procedure (identified by CPT/HCPCS code) in the United States.

**Source URL**: https://www.cms.gov/medicare/payment/fee-schedules/physician/look-up-tool
Download the **National Payment Amount File** for the current year.

**Key columns to extract from the CSV**:
- `HCPCS`: The CPT/HCPCS procedure code (e.g., "99214")
- `DESCRIPTION` or `SHORT_DESCRIPTION`: Human-readable name
- `NON_FACILITY_NA_PAYMENT`: What Medicare pays for this in an outpatient/office setting
- `FACILITY_NA_PAYMENT`: What Medicare pays in a hospital-based setting
- `STATUS_CODE`: Indicates if code is active
- `MULT_SURG`: Multiple surgery reduction indicator

**Database schema**:

```sql
-- Core pricing table
CREATE TABLE medicare_rates (
    cpt_code TEXT NOT NULL,
    description TEXT,
    non_facility_price REAL,
    facility_price REAL,
    status_code TEXT,
    PRIMARY KEY (cpt_code)
);

-- Index for fast lookups
CREATE INDEX idx_cpt ON medicare_rates(cpt_code);

-- CCI edits for unbundling detection
-- If (code_a, code_b) exists in this table, they should NOT be billed together
CREATE TABLE cci_edits (
    column1_code TEXT NOT NULL,       -- The comprehensive/bundled code
    column2_code TEXT NOT NULL,       -- The component code that's included
    effective_date TEXT,
    deletion_date TEXT,               -- NULL if still active
    modifier_indicator TEXT,          -- 0 = never allowed together, 1 = allowed with modifier
    PRIMARY KEY (column1_code, column2_code)
);

CREATE INDEX idx_cci_col1 ON cci_edits(column1_code);
CREATE INDEX idx_cci_col2 ON cci_edits(column2_code);

-- Optional: Hospital-specific rates for richer comparison
CREATE TABLE hospital_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hospital_name TEXT NOT NULL,
    cpt_code TEXT NOT NULL,
    negotiated_rate REAL,
    payer_name TEXT,
    plan_type TEXT
);

-- State-specific billing protection laws
CREATE TABLE state_laws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_code TEXT NOT NULL,             -- e.g., "VA", "CA", "NY"
    state_name TEXT NOT NULL,
    law_name TEXT NOT NULL,               -- e.g., "Virginia Balance Billing Protection Act"
    law_citation TEXT NOT NULL,           -- e.g., "Va. Code § 38.2-3445.01"
    category TEXT NOT NULL,               -- "balance_billing" | "surprise_billing" | "price_transparency" | "dispute_rights" | "payment_plan"
    summary TEXT NOT NULL,                -- Plain-English summary of the protection
    applies_to TEXT,                       -- "emergency" | "in_network_facility" | "all" | etc.
    effective_date TEXT,
    url TEXT                              -- Link to the actual statute if available
);

CREATE INDEX idx_state_laws ON state_laws(state_code);
CREATE INDEX idx_state_laws_category ON state_laws(state_code, category);
```

**Seed script** (`backend/db/seed_db.py`):

```python
import sqlite3
import pandas as pd
import json

def seed_database():
    conn = sqlite3.connect("backend/db/pricing.db")

    # Load CMS fee schedule
    df = pd.read_csv("backend/data/cms_fee_schedule.csv")
    # Filter to relevant columns, rename, clean
    df_clean = df[["HCPCS", "DESCRIPTION", "NON_FACILITY_NA_PAYMENT", "FACILITY_NA_PAYMENT", "STATUS_CODE"]]
    df_clean.columns = ["cpt_code", "description", "non_facility_price", "facility_price", "status_code"]
    # Drop rows where both prices are null
    df_clean = df_clean.dropna(subset=["non_facility_price", "facility_price"], how="all")
    df_clean.to_sql("medicare_rates", conn, if_exists="replace", index=False)

    # Load CCI edits
    cci = pd.read_csv("backend/data/cci_edits.csv")
    cci.to_sql("cci_edits", conn, if_exists="replace", index=False)

    # Load state laws
    with open("backend/data/state_laws.json", "r") as f:
        state_laws = json.load(f)
    df_laws = pd.DataFrame(state_laws)
    df_laws.to_sql("state_laws", conn, if_exists="replace", index=False)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_cpt ON medicare_rates(cpt_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cci_col1 ON cci_edits(column1_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cci_col2 ON cci_edits(column2_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_laws ON state_laws(state_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state_laws_category ON state_laws(state_code, category)")
    conn.commit()
    conn.close()
    print(f"Database seeded: {len(df_clean)} CPT codes, {len(cci)} CCI edit pairs, {len(df_laws)} state law entries")

if __name__ == "__main__":
    seed_database()
```

---

## Backend API

### FastAPI Application Setup (`backend/main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import ALLOWED_ORIGINS
from routers import analyze, explore

app = FastAPI(title="Apollo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(explore.router, prefix="/api")
```

Run with: `cd backend && uvicorn main:app --reload --port 8000`

### Endpoints (`backend/routers/analyze.py`)

#### `POST /api/analyze`
**Purpose**: Main endpoint. Accepts a bill image/PDF, runs the full analysis pipeline, returns all results.

**Request**:
```
Content-Type: multipart/form-data

Fields:
  file: File (required) — PNG, JPG, JPEG, or PDF of medical bill
  state: string (optional, default "VA") — Patient's state for state-specific regulations
  facility_type: string (optional, default "non_facility") — "facility" or "non_facility" to determine which Medicare rate to compare against
```

**Response** (200 OK):
```json
{
  "parsed_bill": {
    "provider": {
      "name": "UVA Health System",
      "address": "1215 Lee St, Charlottesville, VA 22903",
      "npi": "1234567890",
      "phone": "434-924-0000"
    },
    "patient": {
      "name": "Jane Doe",
      "account_number": "ACC-12345",
      "date_of_service": "2025-11-15",
      "insurance": "Anthem BCBS"
    },
    "line_items": [
      {
        "id": 1,
        "description": "Office Visit - Level 4",
        "cpt_code": "99214",
        "quantity": 1,
        "unit_charge": 350.00,
        "total_charge": 350.00,
        "date": "2025-11-15"
      }
    ],
    "total_billed": 650.00,
    "insurance_paid": 280.00,
    "adjustments": 0.00,
    "patient_responsibility": 370.00,
    "parsing_confidence": 0.92
  },
  "benchmarks": [
    {
      "line_item_id": 1,
      "cpt_code": "99214",
      "description": "Office Visit - Level 4",
      "charged": 350.00,
      "medicare_rate": 128.88,
      "fair_price_low": 193.32,
      "fair_price_mid": 257.76,
      "fair_price_high": 322.20,
      "overcharge_ratio": 1.36,
      "potential_savings": 92.24,
      "severity": "moderate",
      "percentile": 72
    }
  ],
  "errors": [
    {
      "id": 1,
      "type": "unbundling",
      "severity": "high",
      "confidence": 0.85,
      "title": "Lab Panel Unbundling Detected",
      "description": "Comprehensive Metabolic Panel (80053) and Basic Metabolic Panel (80048) were billed separately on the same date. BMP is a clinical subset of CMP — only one should be billed.",
      "affected_items": [
        { "cpt_code": "80053", "description": "Comprehensive Metabolic Panel", "charge": 225.00 },
        { "cpt_code": "80048", "description": "Basic Metabolic Panel", "charge": 150.00 }
      ],
      "estimated_overcharge": 150.00,
      "regulation": "CMS Correct Coding Initiative (CCI), Chapter 1 — Mutually exclusive codes",
      "recommendation": "Request removal of the BMP charge (80048). The CMP (80053) includes all BMP components."
    }
  ],
  "dispute_letter": "Dear Billing Department,\n\nI am writing to formally dispute...",
  "state_laws": [
    {
      "law_name": "Virginia Balance Billing Protection Act",
      "law_citation": "Va. Code § 38.2-3445.01",
      "category": "balance_billing",
      "summary": "Virginia law prohibits out-of-network providers at in-network facilities from balance billing patients for emergency services. Patients are only responsible for their in-network cost-sharing amounts.",
      "applies_to": "emergency",
      "url": "https://law.lis.virginia.gov/vacode/title38.2/chapter34/section38.2-3445.01/"
    }
  ],
  "summary": {
    "total_billed": 650.00,
    "estimated_fair_total": 340.00,
    "total_potential_savings": 310.00,
    "savings_from_overcharges": 200.00,
    "savings_from_errors": 110.00,
    "overall_confidence": 0.78,
    "items_flagged": 3,
    "items_fair": 1,
    "errors_found": 1
  }
}
```

**Error responses**:
- `400`: Invalid file type or empty file
- `422`: Bill could not be parsed (unreadable image, not a medical bill)
- `500`: Gemini API error or internal failure

#### `POST /api/generate-letter`
**Purpose**: Regenerate the dispute letter after user has reviewed/edited which issues to include.

**Request** (JSON):
```json
{
  "parsed_bill": { ... },
  "selected_benchmarks": [ ... ],
  "selected_errors": [ ... ],
  "patient_state": "VA",
  "additional_context": "I was told this would be covered by my insurance."
}
```

**Response** (200 OK):
```json
{
  "dispute_letter": "Dear Billing Department,\n\n..."
}
```

#### `GET /api/lookup/{cpt_code}`
**Purpose**: Look up fair pricing for a specific CPT code by exact code match.

**Response** (200 OK):
```json
{
  "cpt_code": "99214",
  "description": "Office or other outpatient visit, established patient, moderate complexity",
  "medicare_non_facility": 128.88,
  "medicare_facility": 93.12,
  "fair_price_range": {
    "low": 193.32,
    "mid": 257.76,
    "high": 322.20
  }
}
```

**Error responses**:
- `404`: CPT code not found in database

#### `GET /api/search-cpt?q={query}&limit={limit}`
**Purpose**: Search CPT codes by description keyword. Powers the CPT Code Explorer feature. Users can type natural language like "MRI" or "knee replacement" and get matching procedures with fair prices.

**Parameters**:
- `q` (required): Search query string, matched against CPT descriptions. Minimum 2 characters.
- `limit` (optional, default 20, max 50): Number of results to return.

**Response** (200 OK):
```json
{
  "query": "MRI knee",
  "results": [
    {
      "cpt_code": "73721",
      "description": "MRI joint of lower extremity without contrast, knee",
      "medicare_non_facility": 198.53,
      "medicare_facility": 198.53,
      "fair_price_range": {
        "low": 297.80,
        "mid": 397.06,
        "high": 496.33
      }
    },
    {
      "cpt_code": "73722",
      "description": "MRI joint of lower extremity with contrast, knee",
      "medicare_non_facility": 261.44,
      "medicare_facility": 261.44,
      "fair_price_range": {
        "low": 392.16,
        "mid": 522.88,
        "high": 653.60
      }
    }
  ],
  "total_results": 2
}
```

**Error responses**:
- `400`: Query too short (less than 2 characters)

**Implementation note**: Use SQLite `LIKE` with wildcards for keyword matching. Split the query into words and require all words to match (AND logic):
```python
# For query "MRI knee":
# WHERE description LIKE '%MRI%' AND description LIKE '%knee%'
words = query.strip().split()
conditions = " AND ".join([f"description LIKE ?" for _ in words])
params = [f"%{word}%" for word in words]
cursor = conn.execute(
    f"SELECT cpt_code, description, non_facility_price, facility_price FROM medicare_rates WHERE {conditions} LIMIT ?",
    params + [limit]
)
```

#### `GET /api/state-laws/{state_code}`
**Purpose**: Return all billing protection laws for a given state. Used by the State Law Panel in the frontend and fed into the dispute letter generator.

**Parameters**:
- `state_code` (path, required): Two-letter state code, e.g., "VA", "CA", "NY"

**Response** (200 OK):
```json
{
  "state_code": "VA",
  "state_name": "Virginia",
  "laws": [
    {
      "law_name": "Virginia Balance Billing Protection Act",
      "law_citation": "Va. Code § 38.2-3445.01",
      "category": "balance_billing",
      "summary": "Prohibits out-of-network providers at in-network facilities from balance billing patients for emergency services.",
      "applies_to": "emergency",
      "effective_date": "2020-01-01",
      "url": "https://law.lis.virginia.gov/vacode/title38.2/chapter34/section38.2-3445.01/"
    },
    {
      "law_name": "Virginia Health Care Price Transparency",
      "law_citation": "Va. Code § 32.1-137.03",
      "category": "price_transparency",
      "summary": "Hospitals must provide price estimates to patients upon request before scheduled services.",
      "applies_to": "all",
      "effective_date": "2018-07-01",
      "url": null
    }
  ],
  "federal_laws": [
    {
      "law_name": "No Surprises Act",
      "law_citation": "Public Law 116-260, Division BB, Title I",
      "category": "surprise_billing",
      "summary": "Federal law protecting patients from surprise out-of-network bills for emergency services and certain non-emergency services at in-network facilities. Effective January 1, 2022.",
      "applies_to": "emergency, in_network_facility_oon_provider",
      "effective_date": "2022-01-01",
      "url": "https://www.cms.gov/nosurprises"
    },
    {
      "law_name": "Hospital Price Transparency Rule",
      "law_citation": "CMS-1717-F2",
      "category": "price_transparency",
      "summary": "Requires all hospitals to publish machine-readable files of standard charges and display shoppable services in a consumer-friendly format.",
      "applies_to": "all",
      "effective_date": "2021-01-01",
      "url": "https://www.cms.gov/hospital-price-transparency"
    }
  ]
}
```

**Error responses**:
- `404`: State code not recognized

### Route Orchestration (`backend/routers/analyze.py`)

This is the critical wiring that chains all services together for the main `/analyze` endpoint:

```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.bill_parser import parse_bill
from services.benchmarker import benchmark_all
from services.error_detector import detect_all_errors
from services.state_laws import get_laws_for_letter, get_state_laws
from services.letter_generator import generate_letter

router = APIRouter()

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "application/pdf"}

@router.post("/analyze")
async def analyze_bill(
    file: UploadFile = File(...),
    state: str = Form("VA"),
    facility_type: str = Form("non_facility"),
):
    # 1. Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}. Upload PNG, JPG, or PDF.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    # 2. Parse the bill (Gemini Vision)
    try:
        parsed_bill = await parse_bill(file_bytes, file.content_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 3. Benchmark each line item against CMS data
    benchmarks = benchmark_all(parsed_bill["line_items"], facility_type)

    # 4. Detect billing errors (rule-based + AI)
    errors = await detect_all_errors(parsed_bill["line_items"])

    # 5. Look up state laws
    state_laws_data = get_state_laws(state)
    state_laws = state_laws_data["laws"] if state_laws_data else []
    federal_laws = state_laws_data["federal_laws"] if state_laws_data else []

    # 6. Generate dispute letter (only if there are issues to dispute)
    has_issues = any(b["severity"] in ("moderate", "high", "critical") for b in benchmarks) or len(errors) > 0
    if has_issues:
        dispute_letter = await generate_letter(
            parsed_bill, benchmarks, errors, state_laws, federal_laws, state
        )
    else:
        dispute_letter = ""

    # 7. Compute summary
    total_billed = parsed_bill.get("total_billed", 0)
    savings_overcharges = sum(b["potential_savings"] for b in benchmarks)
    savings_errors = sum(e.get("estimated_overcharge", 0) or 0 for e in errors)
    fair_total = total_billed - savings_overcharges - savings_errors
    items_flagged = sum(1 for b in benchmarks if b["severity"] in ("moderate", "high", "critical"))
    items_fair = sum(1 for b in benchmarks if b["severity"] == "fair")

    avg_confidence = 0
    confidence_sources = [b.get("overcharge_ratio") for b in benchmarks if b.get("overcharge_ratio")] + \
                         [e.get("confidence", 0) for e in errors]
    if confidence_sources:
        avg_confidence = round(sum(min(c, 1) for c in confidence_sources if isinstance(c, (int, float))) / len(confidence_sources), 2)

    summary = {
        "total_billed": total_billed,
        "estimated_fair_total": round(max(fair_total, 0), 2),
        "total_potential_savings": round(savings_overcharges + savings_errors, 2),
        "savings_from_overcharges": round(savings_overcharges, 2),
        "savings_from_errors": round(savings_errors, 2),
        "overall_confidence": avg_confidence,
        "items_flagged": items_flagged,
        "items_fair": items_fair,
        "errors_found": len(errors),
    }

    return {
        "parsed_bill": parsed_bill,
        "benchmarks": benchmarks,
        "errors": errors,
        "dispute_letter": dispute_letter,
        "state_laws": state_laws,
        "federal_laws": federal_laws,
        "summary": summary,
    }
```

---

## Component 1: Bill Parsing Engine

### Purpose
Accept a medical bill image or PDF. Use Gemini's vision capability to extract all structured data into a consistent JSON schema, regardless of how the bill is formatted.

### Why Gemini Vision (not traditional OCR)
Medical bills have no standard format. Every hospital, lab, and physician group formats them differently. Some print CPT codes, many don't. Some show insurance adjustments, others show raw charges only. Traditional OCR + regex would require hundreds of format-specific rules. Gemini Vision can understand the semantic layout of any bill format and extract the meaning, not just the text.

### Implementation (`backend/services/bill_parser.py`)

```python
from google import genai
from google.genai import types
import base64
import json
import re
from pdf2image import convert_from_bytes
from PIL import Image
import io
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

BILL_PARSING_PROMPT = """You are a medical billing expert. Analyze this medical bill image and extract ALL structured data.

Return ONLY valid JSON (no markdown fences, no explanation) with this exact schema:

{
  "provider": {
    "name": string,
    "address": string or null,
    "npi": string or null,
    "phone": string or null
  },
  "patient": {
    "name": string or null,
    "account_number": string or null,
    "date_of_service": "YYYY-MM-DD" or null,
    "insurance": string or null
  },
  "line_items": [
    {
      "description": string (exact text from bill),
      "cpt_code": string (extract from bill if printed, otherwise infer the most likely CPT/HCPCS code based on the description),
      "cpt_inferred": boolean (true if you inferred the code, false if it was printed on the bill),
      "quantity": number (default 1),
      "unit_charge": number,
      "total_charge": number,
      "date": "YYYY-MM-DD" or null
    }
  ],
  "total_billed": number,
  "insurance_paid": number or null,
  "adjustments": number or null,
  "patient_responsibility": number or null
}

IMPORTANT RULES:
- Extract EVERY line item, even small charges like supplies or facility fees
- If CPT codes are not printed on the bill, INFER them from the description. Use your knowledge of medical billing codes. Set cpt_inferred to true.
- If a line item description is ambiguous, pick the most common CPT code for that service
- All monetary values should be plain numbers (no $ signs, no commas)
- If date_of_service appears once at the top, apply it to all line items
- If the bill shows both "amount billed" and "amount owed", use "amount billed" as the charge for each line item
- Parse ALL pages if multiple images are provided
"""

async def parse_bill(file_bytes: bytes, content_type: str) -> dict:
    """Parse a medical bill image or PDF into structured data."""

    # Convert PDF to images if needed
    if content_type == "application/pdf":
        images = convert_from_bytes(file_bytes, dpi=200)
        image_parts = []
        for img in images:
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            image_parts.append(
                types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/png")
            )
    else:
        image_parts = [
            types.Part.from_bytes(data=file_bytes, mime_type=content_type)
        ]

    # Build the content parts: all images + the prompt
    contents = image_parts + [BILL_PARSING_PROMPT]

    response = client.models.generate_content(
        model="gemini-2.5-pro-preview-05-06",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.1,  # Low temperature for structured extraction
            max_output_tokens=4096,
        ),
    )

    # Parse the response — handle potential markdown fencing
    raw_text = response.text
    cleaned = re.sub(r"```json\s*|\s*```", "", raw_text).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: try to find JSON object in the response
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            raise ValueError("Gemini did not return valid JSON. Raw response: " + raw_text[:500])

    # Validate required fields exist
    validate_parsed_bill(parsed)

    # Add sequential IDs to line items
    for i, item in enumerate(parsed.get("line_items", []), start=1):
        item["id"] = i

    # Calculate parsing confidence based on how many fields were successfully extracted
    parsed["parsing_confidence"] = calculate_confidence(parsed)

    return parsed


def validate_parsed_bill(data: dict):
    """Ensure the parsed bill has minimum required fields."""
    if "line_items" not in data or len(data["line_items"]) == 0:
        raise ValueError("No line items could be extracted from this bill.")
    for item in data["line_items"]:
        if "total_charge" not in item or item["total_charge"] is None:
            raise ValueError(f"Line item missing charge amount: {item.get('description', 'unknown')}")
        if "cpt_code" not in item or item["cpt_code"] is None:
            raise ValueError(f"Could not determine CPT code for: {item.get('description', 'unknown')}")


def calculate_confidence(data: dict) -> float:
    """Estimate confidence in the parsing quality (0-1)."""
    score = 0.0
    total = 0.0

    # Provider info
    total += 3
    if data.get("provider", {}).get("name"): score += 1
    if data.get("provider", {}).get("address"): score += 1
    if data.get("provider", {}).get("npi"): score += 1

    # Patient info
    total += 2
    if data.get("patient", {}).get("date_of_service"): score += 1
    if data.get("patient", {}).get("account_number"): score += 1

    # Line items
    for item in data.get("line_items", []):
        total += 3
        if item.get("cpt_code"): score += 1
        if not item.get("cpt_inferred", True): score += 1  # Bonus for printed codes
        if item.get("total_charge") is not None: score += 1

    # Totals
    total += 2
    if data.get("total_billed"): score += 1
    if data.get("patient_responsibility") is not None: score += 1

    return round(score / max(total, 1), 2)
```

### Edge Cases
- **No CPT codes on bill**: The prompt instructs Gemini to infer them. The `cpt_inferred` boolean flag tells downstream components (and the user) which codes were guessed vs. printed.
- **Multi-page PDF**: All pages are converted to images and sent together in one Gemini call.
- **EOB format**: Explanation of Benefits documents have a different structure (insurer info, allowed amounts, copay breakdowns). The prompt is general enough to handle both formats.
- **Blurry or rotated images**: Gemini Vision handles moderate image quality issues. For very low quality, the confidence score will be low, and the UI should show a warning.
- **Not a medical bill**: If someone uploads a random document, validation will fail (no line items extracted). Return a clear error message.

---

## Component 2: Fair Price Benchmarking

### Purpose
For each parsed line item, look up the Medicare-allowed rate and compute whether the patient is being overcharged. Produce a severity rating and potential savings amount.

### Pricing Model
Medicare rates represent what the government pays for a procedure. Commercial insurers typically pay 1.5x to 2.5x the Medicare rate. We use these multipliers to create a "fair price range":
- **Low**: Medicare rate × 1.5 (aggressive estimate — what a good negotiator might achieve)
- **Mid**: Medicare rate × 2.0 (reasonable market rate for commercially insured patients)
- **High**: Medicare rate × 2.5 (upper end of typical commercial rates)

If the billed amount exceeds the "high" end, the patient is almost certainly being overcharged.

### Severity Classification
- **fair** (green): `overcharge_ratio <= 1.5` — Charge is within or below the fair price range
- **moderate** (yellow): `1.5 < overcharge_ratio <= 2.5` — Somewhat above fair market, worth questioning
- **high** (orange): `2.5 < overcharge_ratio <= 4.0` — Significantly above fair market, likely dispute-worthy
- **critical** (red): `overcharge_ratio > 4.0` — Extreme overcharge, strong case for dispute

### Implementation (`backend/services/benchmarker.py`)

```python
import sqlite3
from typing import Optional
from config import DATABASE_PATH

DB_PATH = DATABASE_PATH

def get_medicare_rate(cpt_code: str, facility_type: str = "non_facility") -> Optional[dict]:
    """Look up the Medicare rate for a CPT code."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT cpt_code, description, non_facility_price, facility_price FROM medicare_rates WHERE cpt_code = ?",
        (cpt_code,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    price = row["facility_price"] if facility_type == "facility" else row["non_facility_price"]

    return {
        "cpt_code": row["cpt_code"],
        "description": row["description"],
        "medicare_rate": price,
    }


def benchmark_line_item(line_item: dict, facility_type: str = "non_facility") -> dict:
    """Benchmark a single line item against Medicare rates."""
    cpt = line_item["cpt_code"]
    charged = line_item["total_charge"]

    rate_info = get_medicare_rate(cpt, facility_type)

    if rate_info is None or rate_info["medicare_rate"] is None or rate_info["medicare_rate"] == 0:
        return {
            "line_item_id": line_item["id"],
            "cpt_code": cpt,
            "description": line_item["description"],
            "charged": charged,
            "medicare_rate": None,
            "fair_price_low": None,
            "fair_price_mid": None,
            "fair_price_high": None,
            "overcharge_ratio": None,
            "potential_savings": 0.0,
            "severity": "unknown",
            "note": f"CPT code {cpt} not found in Medicare fee schedule. This may be a non-covered service or an incorrect code."
        }

    medicare_rate = rate_info["medicare_rate"]
    fair_low = round(medicare_rate * 1.5, 2)
    fair_mid = round(medicare_rate * 2.0, 2)
    fair_high = round(medicare_rate * 2.5, 2)

    overcharge_ratio = round(charged / fair_mid, 2) if fair_mid > 0 else 0
    potential_savings = round(max(0, charged - fair_mid), 2)

    if overcharge_ratio <= 1.5:
        severity = "fair"
    elif overcharge_ratio <= 2.5:
        severity = "moderate"
    elif overcharge_ratio <= 4.0:
        severity = "high"
    else:
        severity = "critical"

    return {
        "line_item_id": line_item["id"],
        "cpt_code": cpt,
        "description": line_item["description"],
        "charged": charged,
        "medicare_rate": medicare_rate,
        "fair_price_low": fair_low,
        "fair_price_mid": fair_mid,
        "fair_price_high": fair_high,
        "overcharge_ratio": overcharge_ratio,
        "potential_savings": potential_savings,
        "severity": severity,
    }


def benchmark_all(line_items: list, facility_type: str = "non_facility") -> list:
    """Benchmark all line items from a parsed bill."""
    return [benchmark_line_item(item, facility_type) for item in line_items]
```

---

## Component 3: Billing Error Detection

### Purpose
Identify common billing errors that go beyond simple overcharging. These are mistakes or manipulative practices in how the bill was coded. Detecting these is the most technically impressive part of the project — it shows the AI doing real clinical reasoning.

### Error Types

#### 1. Duplicate Charges
**What**: Same CPT code billed more than once on the same date of service.
**Detection**: Group line items by (cpt_code, date). If any group has count > 1 and doesn't have a legitimate modifier, flag it.
**Confidence**: 0.90+ when detected (almost always an error)
**Example**: Two charges for CPT 99214 on Nov 15 — you didn't have two office visits in one day.

#### 2. Unbundling
**What**: Billing multiple component codes separately when a single comprehensive code should cover them all. This inflates the total bill.
**Detection**: Check every pair of CPT codes on the bill against the CMS CCI (Correct Coding Initiative) edits table. If a pair appears in the CCI edits, the component code should not have been billed separately.
**Confidence**: 0.85 (CCI edits are official CMS rules)
**Example**: Billing both 80048 (Basic Metabolic Panel) and 80053 (Comprehensive Metabolic Panel) — the CMP includes everything in the BMP.

#### 3. Upcoding
**What**: Billing for a more complex/expensive version of a service than what was actually provided.
**Detection**: Use Gemini to analyze whether the descriptions and combination of services suggest a lower-complexity visit than what was coded. E/M visit levels (99211-99215) are the most common upcoding target.
**Confidence**: 0.50-0.75 (requires clinical judgment, can't be certain without medical records)
**Example**: A routine follow-up for a stable condition billed as 99215 (high complexity) instead of 99213 (low complexity).

#### 4. Unlikely Service Combinations
**What**: Services billed together that don't make clinical sense for the same visit.
**Detection**: Use Gemini to reason about whether the combination of procedures is clinically plausible.
**Confidence**: 0.40-0.65 (speculative, flag for user review)
**Example**: A dermatology consultation and a cardiac stress test on the same visit to the same provider.

### Implementation (`backend/services/error_detector.py`)

```python
import sqlite3
from google import genai
from google.genai import types
import json
import re
from config import GEMINI_API_KEY, DATABASE_PATH

client = genai.Client(api_key=GEMINI_API_KEY)
DB_PATH = DATABASE_PATH

# ──────────────────────────────
# PASS 1: Rule-Based Detection
# ──────────────────────────────

def detect_duplicates(line_items: list) -> list:
    """Find duplicate charges (same CPT code, same date)."""
    errors = []
    seen = {}
    for item in line_items:
        key = (item["cpt_code"], item.get("date"))
        if key in seen:
            errors.append({
                "type": "duplicate",
                "severity": "high",
                "confidence": 0.92,
                "title": f"Duplicate Charge: {item['description']}",
                "description": f"CPT code {item['cpt_code']} ({item['description']}) appears to be billed twice on {item.get('date', 'the same date')}. Unless two identical procedures were genuinely performed, this is likely an error.",
                "affected_items": [seen[key], item],
                "estimated_overcharge": item["total_charge"],
                "regulation": "CMS Claims Processing Manual, Chapter 23 — duplicate claims",
                "recommendation": "Request removal of the duplicate charge and a refund of the duplicated amount."
            })
        else:
            seen[key] = item
    return errors


def detect_unbundling(line_items: list) -> list:
    """Find codes that should be bundled per CCI edits."""
    errors = []
    conn = sqlite3.connect(DB_PATH)

    codes = [item["cpt_code"] for item in line_items]
    code_to_item = {item["cpt_code"]: item for item in line_items}

    for i, code_a in enumerate(codes):
        for code_b in codes[i+1:]:
            # Check both directions: (a,b) and (b,a)
            cursor = conn.execute(
                """SELECT column1_code, column2_code, modifier_indicator
                   FROM cci_edits
                   WHERE (column1_code = ? AND column2_code = ?)
                      OR (column1_code = ? AND column2_code = ?)""",
                (code_a, code_b, code_b, code_a)
            )
            row = cursor.fetchone()
            if row:
                comprehensive_code = row[0]
                component_code = row[1]
                comp_item = code_to_item.get(component_code, code_to_item.get(code_b))
                errors.append({
                    "type": "unbundling",
                    "severity": "high",
                    "confidence": 0.85,
                    "title": f"Unbundling: {comprehensive_code} + {component_code}",
                    "description": f"CPT {component_code} ({code_to_item.get(component_code, {}).get('description', 'N/A')}) is a component of {comprehensive_code} ({code_to_item.get(comprehensive_code, {}).get('description', 'N/A')}). Per CMS Correct Coding Initiative rules, these should not be billed separately.",
                    "affected_items": [code_to_item.get(comprehensive_code, {}), code_to_item.get(component_code, {})],
                    "estimated_overcharge": comp_item.get("total_charge", 0) if comp_item else 0,
                    "regulation": "CMS National Correct Coding Initiative (NCCI/CCI) Edits — Procedure-to-Procedure (PTP) edits",
                    "recommendation": f"Request removal of the component code ({component_code}) charge. The comprehensive code ({comprehensive_code}) already covers this service."
                })

    conn.close()
    return errors


# ──────────────────────────────
# PASS 2: AI-Powered Detection
# ──────────────────────────────

ERROR_DETECTION_PROMPT = """You are a medical billing auditor. Analyze the following medical bill line items for potential billing errors.

LINE ITEMS:
{line_items_json}

ALREADY DETECTED (do not repeat these):
{already_found_json}

Check for:
1. UPCODING: Is any E/M visit level (99211-99215) higher than what the combination of other services suggests? A routine visit with basic labs is typically 99213, not 99214 or 99215.
2. UNLIKELY COMBINATIONS: Are any services clinically implausible to have occurred together in the same visit?
3. QUESTIONABLE CHARGES: Are there facility fees, "miscellaneous" charges, or supply charges that seem unusual?

For each issue found, return JSON (no markdown fences):
[
  {{
    "type": "upcoding" | "unlikely_combination" | "questionable_charge",
    "severity": "low" | "medium" | "high",
    "confidence": 0.0-1.0,
    "title": "Short title",
    "description": "Detailed explanation in plain English",
    "affected_cpt_codes": ["99214", ...],
    "estimated_overcharge": number or null,
    "recommendation": "What the patient should do"
  }}
]

If no additional issues are found, return an empty array: []

Be conservative. Only flag issues where you have reasonable confidence. Do not repeat errors already detected.
"""

async def detect_ai_errors(line_items: list, already_found: list) -> list:
    """Use Gemini to detect upcoding and unlikely combinations."""
    prompt = ERROR_DETECTION_PROMPT.format(
        line_items_json=json.dumps(line_items, indent=2),
        already_found_json=json.dumps([e["type"] + ": " + e["title"] for e in already_found])
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro-preview-05-06",
        contents=[prompt],
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=2048,
        ),
    )

    raw_text = response.text
    cleaned = re.sub(r"```json\s*|\s*```", "", raw_text).strip()

    try:
        ai_errors = json.loads(cleaned)
    except json.JSONDecodeError:
        return []  # If AI response isn't valid JSON, skip AI errors rather than crash

    # Enrich AI errors with regulation citations and map affected items
    code_to_item = {item["cpt_code"]: item for item in line_items}
    enriched = []
    for error in ai_errors:
        affected_items = [code_to_item[c] for c in error.get("affected_cpt_codes", []) if c in code_to_item]
        enriched.append({
            "type": error["type"],
            "severity": error.get("severity", "medium"),
            "confidence": error.get("confidence", 0.5),
            "title": error["title"],
            "description": error["description"],
            "affected_items": affected_items,
            "estimated_overcharge": error.get("estimated_overcharge"),
            "regulation": get_regulation_citation(error["type"]),
            "recommendation": error.get("recommendation", "Review this charge with your provider.")
        })

    return enriched


def get_regulation_citation(error_type: str) -> str:
    """Return the relevant regulation for an error type."""
    citations = {
        "upcoding": "CMS Evaluation and Management (E/M) Documentation Guidelines; OIG Compliance Program Guidance",
        "unlikely_combination": "CMS Medically Unlikely Edits (MUE); Clinical plausibility review",
        "questionable_charge": "Hospital Price Transparency Final Rule (CMS-1717-F2); No Surprises Act, Section 112",
        "duplicate": "CMS Claims Processing Manual, Chapter 23",
        "unbundling": "CMS National Correct Coding Initiative (NCCI) Edits",
    }
    return citations.get(error_type, "CMS billing guidelines")


# ──────────────────────────────
# Combined Detection Pipeline
# ──────────────────────────────

async def detect_all_errors(line_items: list) -> list:
    """Run all error detection (rule-based + AI) and return combined results."""
    # Pass 1: Rule-based (fast, high confidence)
    errors = []
    errors.extend(detect_duplicates(line_items))
    errors.extend(detect_unbundling(line_items))

    # Pass 2: AI-powered (slower, variable confidence)
    ai_errors = await detect_ai_errors(line_items, errors)
    errors.extend(ai_errors)

    # Assign sequential IDs
    for i, error in enumerate(errors, start=1):
        error["id"] = i

    # Sort by confidence descending
    errors.sort(key=lambda e: e.get("confidence", 0), reverse=True)

    return errors
```

---

## Component 4: Dispute Letter Generator

### Purpose
Generate a professional, ready-to-send dispute letter that cites specific pricing data and regulations. The letter should sound like it was written by a medical billing advocate — because that's what gets results.

### Letter Requirements
- Addressed to the provider's billing department by name
- References the patient's account number and date of service
- Lists each disputed charge with the specific CPT code and dollar amounts
- Cites Medicare fair pricing data for overcharges (with exact numbers)
- Cites CCI edit rules or other regulations for billing errors
- **Includes a "Your Rights Under State and Federal Law" section** citing applicable state statutes by name and citation, plus federal protections (No Surprises Act, Hospital Price Transparency Rule)
- Requests an itemized re-review and correction
- Sets a 30-day deadline for response
- Mentions escalation to state insurance commissioner if unresolved, citing the specific laws that may have been violated
- Firm but professional tone — not hostile, not meek

### Implementation (`backend/services/letter_generator.py`)

```python
from google import genai
from google.genai import types
import json
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

LETTER_PROMPT = """You are a medical billing advocate writing a formal dispute letter on behalf of a patient. Generate a professional dispute letter based on the following analysis.

PATIENT INFORMATION:
- Name: {patient_name}
- Account Number: {account_number}
- Date of Service: {date_of_service}

PROVIDER:
- Name: {provider_name}
- Address: {provider_address}

PRICING ISSUES FOUND:
{benchmarks_json}

BILLING ERRORS FOUND:
{errors_json}

TOTAL BILLED: ${total_billed}
ESTIMATED FAIR PRICE: ${fair_total}
POTENTIAL SAVINGS: ${potential_savings}

PATIENT'S STATE: {state}

APPLICABLE STATE LAWS:
{state_laws_json}

APPLICABLE FEDERAL LAWS:
{federal_laws_json}

ADDITIONAL CONTEXT FROM PATIENT: {additional_context}

LETTER REQUIREMENTS:
- Format as a proper business letter with today's date
- Address to "Billing Department" at the provider
- Open with a clear statement of purpose: disputing specific charges
- For EACH pricing issue with severity "moderate", "high", or "critical": state the CPT code, what was charged, what the Medicare rate is, and what a fair commercial rate would be. Cite "CMS Medicare Physician Fee Schedule" as your source.
- For EACH billing error: explain what the error is, cite the relevant regulation, and state the expected correction amount
- Include a dedicated section titled "Your Rights Under State and Federal Law" that cites each applicable state law by name and statute citation (e.g., "Under the Virginia Balance Billing Protection Act, Va. Code § 38.2-3445.01, ..."). Also cite applicable federal protections like the No Surprises Act.
- Request a complete itemized re-review of all charges
- Request a written response within 30 business days
- State that if the dispute is not resolved satisfactorily, you will escalate to the {state} State Insurance Commissioner and/or file a complaint with CMS, citing the specific laws that may have been violated
- Close professionally
- The tone should be firm, factual, and professional. Not threatening, not apologetic.
- Do NOT include placeholder brackets or instructions — this should be ready to print and mail

Return ONLY the letter text, no additional commentary.
"""

async def generate_letter(parsed_bill: dict, benchmarks: list, errors: list, state_laws: list, federal_laws: list, state: str = "VA", additional_context: str = "") -> str:
    """Generate a dispute letter from analysis results, including state-specific legal citations."""

    # Filter benchmarks to only include moderate+ severity
    flagged_benchmarks = [b for b in benchmarks if b.get("severity") in ("moderate", "high", "critical")]

    patient = parsed_bill.get("patient", {})
    provider = parsed_bill.get("provider", {})

    fair_total = sum(b.get("fair_price_mid", b.get("charged", 0)) for b in benchmarks)
    total_billed = parsed_bill.get("total_billed", 0)
    potential_savings = round(total_billed - fair_total, 2)

    prompt = LETTER_PROMPT.format(
        patient_name=patient.get("name", "[Patient Name]"),
        account_number=patient.get("account_number", "[Account Number]"),
        date_of_service=patient.get("date_of_service", "[Date]"),
        provider_name=provider.get("name", "[Provider Name]"),
        provider_address=provider.get("address", "[Provider Address]"),
        benchmarks_json=json.dumps(flagged_benchmarks, indent=2),
        errors_json=json.dumps(errors, indent=2),
        total_billed=total_billed,
        fair_total=round(fair_total, 2),
        potential_savings=max(0, potential_savings),
        state=state,
        state_laws_json=json.dumps(state_laws, indent=2),
        federal_laws_json=json.dumps(federal_laws, indent=2),
        additional_context=additional_context or "None provided.",
    )

    response = client.models.generate_content(
        model="gemini-2.5-pro-preview-05-06",
        contents=[prompt],
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=3000,
        ),
    )

    return response.text.strip()
```

---

## Component 5: Frontend Application

### Overall Design Direction
- **Aesthetic**: Clean, trustworthy, medical-professional. Think: health-tech startup, not hospital software.
- **Color palette**: White/off-white background. Primary blue (#2563EB) for trust. Green (#16A34A) for "fair" prices and savings. Red/orange (#DC2626 / #EA580C) for overcharges and errors. Dark gray (#1F2937) for text.
- **Typography**: Use a clean sans-serif. Recommended: `DM Sans` for headings, `Inter` or system fonts for body (in this case Inter is fine since it's a data-heavy dashboard, not a creative site).
- **Layout**: Single-page app with three states — Upload → Loading → Results. No routing needed for hackathon.

### Screen 1: Upload Screen (`UploadScreen.jsx`)

**Layout**:
- Centered card on a subtle gradient or textured background
- Apollo logo + tagline at top: "Get a second opinion on your medical bill."
- Large drag-and-drop zone (dashed border, icon, "Drop your bill here or click to upload")
- Accepted formats note: "Supports PNG, JPG, PDF"
- Below the drop zone: "Or try a sample" with 3 clickable thumbnails of sample bills
  - Sample A: "ER Visit with Labs" (has errors)
  - Sample B: "Routine Checkup" (has overcharges)
  - Sample C: "Clean Bill" (passes checks)
- The sample bills are critical — they guarantee a smooth demo even if a live upload fails

**State management**:
```javascript
const [file, setFile] = useState(null);
const [preview, setPreview] = useState(null); // Thumbnail of uploaded bill
const [isAnalyzing, setIsAnalyzing] = useState(false);
const [results, setResults] = useState(null);
const [error, setError] = useState(null);
```

**On file select**: Show thumbnail preview, enable "Analyze" button. On click or on drop, immediately start the analysis (no extra confirmation step — speed matters in a demo).

### Screen 2: Loading Screen (`LoadingScreen.jsx`)

**Layout**:
- Centered, minimal
- Apollo logo with a subtle pulse animation
- Rotating status messages that describe what's happening:
  1. "Reading your bill..." (0-2 seconds)
  2. "Identifying procedure codes..." (2-4 seconds)
  3. "Checking fair market prices..." (4-6 seconds)
  4. "Scanning for billing errors..." (6-8 seconds)
  5. "Looking up your state protections..." (8-10 seconds)
  6. "Generating your report..." (10-12 seconds)
- Progress bar or step indicator showing which phase is active
- The messages should advance on timers regardless of actual backend progress — this is a perceived-performance trick. The real API call is one POST that returns everything.

**Why this matters for the demo**: Judges see the steps and understand the pipeline is doing real work, even though it's one API call under the hood.

### Screen 3: Results Dashboard (`ResultsDashboard.jsx`)

This is the main event. It should feel like opening a professional audit report.

**Section order** (top to bottom):

#### 3a. Savings Summary Header (`SavingsSummary.jsx`)
- Full-width banner at the top
- Large text: "Apollo found **$310.00** in potential savings"
- The number should animate counting up from $0 when the results load
- Below: "X items flagged · Y billing errors found · Z items fairly priced"
- Two small badges: "Savings from overcharges: $200" and "Savings from errors: $110"
- Background: subtle gradient from green to blue

#### 3b. Bill Summary Table (`BillSummary.jsx`)
- Clean table showing all parsed line items
- Columns: Description | CPT Code | Date | Charged | Fair Price | Status
- Status column: colored badges — "Fair" (green), "Overcharged" (orange/red), "Error" (red with icon)
- CPT codes that were inferred (not printed on bill) get a small "inferred" tooltip icon
- Row click expands to show benchmarking details for that item
- Total row at bottom with billed vs. fair comparison

#### 3c. Price Comparison Chart (`PriceComparison.jsx`)
- **Horizontal bar chart** (Recharts `BarChart` with `layout="vertical"`)
- One row per line item
- Each row shows:
  - A red/orange bar: what you were charged
  - A green bar: the fair price (mid estimate)
  - A blue dotted line: Medicare rate
  - A green shaded band: fair price range (low to high)
- Items sorted by overcharge_ratio descending (worst offenders first)
- Labels show dollar amounts on each bar

**Recharts example structure**:
```jsx
<BarChart layout="vertical" data={benchmarks}>
  <XAxis type="number" tickFormatter={(v) => `$${v}`} />
  <YAxis type="category" dataKey="description" width={200} />
  <Bar dataKey="charged" fill="#DC2626" name="Your Charge" />
  <Bar dataKey="fair_price_mid" fill="#16A34A" name="Fair Price" />
  <ReferenceLine x={medicareRate} stroke="#2563EB" strokeDasharray="3 3" label="Medicare" />
</BarChart>
```

#### 3d. Error Detection Panel (`ErrorPanel.jsx`)
- Card-based layout, one card per error
- Each card contains:
  - **Header**: Error type badge (color-coded) + title
  - **Confidence bar**: Visual meter from 0-100% with label
  - **Description**: Plain-English explanation (2-3 sentences)
  - **Affected items**: List of CPT codes and charges involved
  - **Estimated overcharge**: Dollar amount in bold red
  - **Regulation**: Cited in a subtle gray box (e.g., "CMS NCCI Edits, PTP")
  - **Recommendation**: What to do about it in green text
- If no errors found, show a positive message: "No billing errors detected. Your bill appears to be coded correctly."

#### 3e. State Law Panel (`StateLawPanel.jsx`)
- Collapsible section titled "Your Rights in {State Name}"
- Card for each applicable state law:
  - **Law name** in bold (e.g., "Virginia Balance Billing Protection Act")
  - **Citation** in monospace (e.g., `Va. Code § 38.2-3445.01`)
  - **Category badge**: color-coded by type — "Balance Billing" (blue), "Surprise Billing" (purple), "Price Transparency" (teal), "Dispute Rights" (green)
  - **Summary**: 1-2 sentence plain-English explanation of the protection
  - **Applies to**: Badge showing "Emergency", "All Services", "In-Network Facility", etc.
  - **Link**: If URL is available, "View Statute →" link opens in new tab
- Separate sub-section for federal laws (No Surprises Act, Hospital Price Transparency Rule) — these apply regardless of state
- If no state-specific laws found, still show the federal protections
- **Why this matters for judges**: It shows the system doesn't just find problems — it arms the patient with their legal rights. The local Virginia angle is especially strong for a UVA hackathon.

#### 3f. Dispute Letter Preview (`DisputeLetter.jsx`)
- Rendered letter in a white "paper" card with subtle shadow (looks like a real letter)
- Monospace or serif font to differentiate from the dashboard
- The letter now includes a "Your Rights Under State and Federal Law" section with specific statute citations pulled from the State Law Engine
- Three action buttons below:
  - **"Download PDF"** — generates a PDF of the letter (use browser print-to-PDF or a library)
  - **"Copy to Clipboard"** — copies plain text
  - **"Edit & Regenerate"** — opens a text editor where user can modify, then re-generate with changes
- The letter should be fully populated with real data — no placeholders visible

### Screen 4: CPT Code Explorer (`CptExplorer.jsx`)

This is a standalone tool accessible from a tab or navigation link alongside the main bill analysis flow. It serves two purposes: (1) lets users independently research fair prices for any procedure, and (2) is a killer demo prop during Q&A when a judge asks "what about X procedure?"

**Layout**:
- Search bar at the top, full-width, prominent. Placeholder text: "Search any procedure — try 'MRI', 'knee replacement', 'colonoscopy'..."
- Debounced search (300ms delay after typing stops, then fires `GET /api/search-cpt?q=...`)
- Results render as a clean card list below the search bar

**Result card for each matching CPT code**:
- **CPT Code** in bold monospace (e.g., `73721`)
- **Description** in regular text (e.g., "MRI joint of lower extremity without contrast, knee")
- **Price comparison bar**: horizontal mini-chart showing Medicare rate vs. fair price range, same visual language as the main dashboard's PriceComparison chart but in a compact single-row format
- **Key numbers displayed**:
  - Medicare Rate: $198.53
  - Fair Price Range: $297 – $496
  - "If you're being charged more than **$496**, you're likely being overcharged"
- **Click to expand**: shows facility vs. non-facility Medicare rates, and a brief explanation of what the procedure entails (use the CMS description)

**Empty state**: Before any search, show a few "popular searches" as clickable pills: "MRI", "X-ray", "Blood work", "Office visit", "Physical therapy", "Colonoscopy". Clicking one auto-fills and triggers the search.

**No results state**: "No procedures found matching '{query}'. Try broader terms — e.g., 'MRI' instead of 'MRI of left knee with contrast'."

**Technical implementation**:
```jsx
const [query, setQuery] = useState("");
const [results, setResults] = useState([]);
const [loading, setLoading] = useState(false);

useEffect(() => {
  if (query.length < 2) { setResults([]); return; }
  const timer = setTimeout(async () => {
    setLoading(true);
    const res = await fetch(`${API_URL}/search-cpt?q=${encodeURIComponent(query)}&limit=20`);
    const data = await res.json();
    setResults(data.results);
    setLoading(false);
  }, 300);
  return () => clearTimeout(timer);
}, [query]);
```

### Navigation
The app has two main views, accessible via a simple tab bar or top nav:
- **"Analyze Bill"** — the upload → results flow (Screens 1-3)
- **"Price Explorer"** — the CPT Code Explorer (Screen 4)

The nav should be minimal — two tabs, clearly labeled, always visible. Default to "Analyze Bill" on load.

### Responsive Design
- Desktop-first (demo will be on a laptop), but basic mobile support for judges who check on phones
- Single-column layout on mobile
- Chart switches to vertical bars on small screens
- Minimum viable: looks good at 1280px width, doesn't break at 375px

---

## Component 6: State Law Engine

### Purpose
Every US state has its own set of medical billing protections on top of federal laws. When Apollo detects issues with a bill, it looks up the patient's state and pulls in the specific laws that protect them. These laws are cited in the dispute letter and displayed in the State Law Panel, transforming Apollo from "you're being overcharged" into "you're being overcharged and here's the law they're violating." This is an enormous credibility boost — both for the user's dispute and for the hackathon demo.

### Data Source: `backend/data/state_laws.json`

This is a hand-curated JSON file. For the hackathon, you need comprehensive coverage of Virginia (since you're at UVA and the demo should be local) plus a handful of other states to show the system is generalizable. Federal laws apply to all states.

**Structure**:
```json
[
  {
    "state_code": "VA",
    "state_name": "Virginia",
    "law_name": "Virginia Balance Billing Protection Act",
    "law_citation": "Va. Code § 38.2-3445.01",
    "category": "balance_billing",
    "summary": "Prohibits out-of-network providers at in-network facilities from balance billing patients for emergency services. Patients are only responsible for in-network cost-sharing amounts (copays, coinsurance, deductibles).",
    "applies_to": "emergency",
    "effective_date": "2020-01-01",
    "url": "https://law.lis.virginia.gov/vacode/title38.2/chapter34/section38.2-3445.01/"
  },
  {
    "state_code": "VA",
    "state_name": "Virginia",
    "law_name": "Virginia Health Care Price Transparency",
    "law_citation": "Va. Code § 32.1-137.03",
    "category": "price_transparency",
    "summary": "Hospitals must provide patients with an estimate of charges upon request prior to non-emergency services. Patients have the right to receive an itemized bill.",
    "applies_to": "all",
    "effective_date": "2018-07-01",
    "url": null
  },
  {
    "state_code": "VA",
    "state_name": "Virginia",
    "law_name": "Virginia Surprise Billing Protection",
    "law_citation": "Va. Code § 38.2-3445.02",
    "category": "surprise_billing",
    "summary": "Patients receiving emergency care or care at an in-network facility from out-of-network providers cannot be billed more than their in-network cost-sharing. Disputes between providers and insurers use an independent dispute resolution process.",
    "applies_to": "emergency, in_network_facility_oon_provider",
    "effective_date": "2021-01-01",
    "url": null
  },
  {
    "state_code": "VA",
    "state_name": "Virginia",
    "law_name": "Patient Right to Itemized Bill",
    "law_citation": "Va. Code § 32.1-137",
    "category": "dispute_rights",
    "summary": "Patients have the right to receive a fully itemized statement of charges. Providers must furnish this within a reasonable time upon request.",
    "applies_to": "all",
    "effective_date": "1992-01-01",
    "url": null
  },
  {
    "state_code": "CA",
    "state_name": "California",
    "law_name": "California Surprise Balance Billing Protection",
    "law_citation": "Cal. Health & Safety Code § 1386.9",
    "category": "balance_billing",
    "summary": "Patients cannot be balance billed for emergency services or by out-of-network providers at in-network facilities. Out-of-pocket costs limited to in-network cost-sharing.",
    "applies_to": "emergency, in_network_facility_oon_provider",
    "effective_date": "2017-07-01",
    "url": null
  },
  {
    "state_code": "NY",
    "state_name": "New York",
    "law_name": "New York Emergency Medical Services and Surprise Bills Law",
    "law_citation": "NY Financial Services Law § 603",
    "category": "surprise_billing",
    "summary": "One of the first state surprise billing laws. Patients only owe their in-network cost-sharing for emergency and surprise out-of-network bills. Disputes go to independent dispute resolution.",
    "applies_to": "emergency, surprise_oon",
    "effective_date": "2015-03-31",
    "url": null
  },
  {
    "state_code": "TX",
    "state_name": "Texas",
    "law_name": "Texas Out-of-Network Billing Protection (SB 1264)",
    "law_citation": "Tex. Insurance Code § 1467",
    "category": "balance_billing",
    "summary": "Patients receiving emergency care or care from an out-of-network provider at an in-network facility are protected from balance billing. Applies to most state-regulated insurance plans.",
    "applies_to": "emergency, in_network_facility_oon_provider",
    "effective_date": "2020-01-01",
    "url": null
  }
]
```

**Federal laws** are hard-coded in the service (they apply to all states):

```python
FEDERAL_LAWS = [
    {
        "law_name": "No Surprises Act",
        "law_citation": "Public Law 116-260, Division BB, Title I",
        "category": "surprise_billing",
        "summary": "Federal law protecting patients from surprise out-of-network bills for emergency services and certain non-emergency services at in-network facilities. Bans balance billing in these scenarios. Requires good-faith cost estimates for uninsured/self-pay patients.",
        "applies_to": "emergency, in_network_facility_oon_provider, uninsured",
        "effective_date": "2022-01-01",
        "url": "https://www.cms.gov/nosurprises"
    },
    {
        "law_name": "Hospital Price Transparency Rule",
        "law_citation": "CMS-1717-F2 (45 CFR Part 180)",
        "category": "price_transparency",
        "summary": "Requires all hospitals to publish machine-readable files of standard charges for all items and services, including gross charges, payer-negotiated rates, and de-identified minimum/maximum rates. Also requires a consumer-friendly display of 300 shoppable services.",
        "applies_to": "all",
        "effective_date": "2021-01-01",
        "url": "https://www.cms.gov/hospital-price-transparency"
    },
    {
        "law_name": "Patient Right to Receive Good Faith Estimate",
        "law_citation": "No Surprises Act, Section 112",
        "category": "dispute_rights",
        "summary": "Uninsured or self-pay patients have the right to a Good Faith Estimate of expected charges before receiving care. If the final bill exceeds the estimate by $400 or more, the patient can initiate a dispute through the Patient-Provider Dispute Resolution process.",
        "applies_to": "uninsured, self_pay",
        "effective_date": "2022-01-01",
        "url": "https://www.cms.gov/nosurprises/consumers/understanding-costs-in-advance"
    }
]
```

### Implementation (`backend/services/state_laws.py`)

```python
import sqlite3
import json
from typing import Optional
from config import DATABASE_PATH

DB_PATH = DATABASE_PATH

FEDERAL_LAWS = [
    {
        "law_name": "No Surprises Act",
        "law_citation": "Public Law 116-260, Division BB, Title I",
        "category": "surprise_billing",
        "summary": "Federal law protecting patients from surprise out-of-network bills for emergency services and certain non-emergency services at in-network facilities. Bans balance billing in these scenarios.",
        "applies_to": "emergency, in_network_facility_oon_provider, uninsured",
        "effective_date": "2022-01-01",
        "url": "https://www.cms.gov/nosurprises"
    },
    {
        "law_name": "Hospital Price Transparency Rule",
        "law_citation": "CMS-1717-F2 (45 CFR Part 180)",
        "category": "price_transparency",
        "summary": "Requires all hospitals to publish machine-readable files of standard charges including gross charges and payer-negotiated rates.",
        "applies_to": "all",
        "effective_date": "2021-01-01",
        "url": "https://www.cms.gov/hospital-price-transparency"
    },
    {
        "law_name": "Patient Right to Good Faith Estimate",
        "law_citation": "No Surprises Act, Section 112",
        "category": "dispute_rights",
        "summary": "Uninsured or self-pay patients can request a Good Faith Estimate before care. If the final bill exceeds the estimate by $400+, they can dispute it through the federal Patient-Provider Dispute Resolution process.",
        "applies_to": "uninsured, self_pay",
        "effective_date": "2022-01-01",
        "url": "https://www.cms.gov/nosurprises/consumers/understanding-costs-in-advance"
    }
]

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"
}


def get_state_laws(state_code: str) -> Optional[dict]:
    """Return all billing protection laws for a given state plus federal laws."""
    state_code = state_code.upper()
    if state_code not in US_STATES:
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM state_laws WHERE state_code = ? ORDER BY category",
        (state_code,)
    )
    rows = cursor.fetchall()
    conn.close()

    state_laws = [dict(row) for row in rows]

    return {
        "state_code": state_code,
        "state_name": US_STATES[state_code],
        "laws": state_laws,
        "federal_laws": FEDERAL_LAWS
    }


def get_laws_for_letter(state_code: str) -> tuple[list, list]:
    """Return state laws and federal laws as separate lists for the letter generator."""
    result = get_state_laws(state_code)
    if result is None:
        return [], FEDERAL_LAWS
    return result["laws"], result["federal_laws"]
```

### Expanding State Coverage

For the hackathon, Virginia + 3-4 other major states is sufficient. To expand later:
- The National Conference of State Legislatures (NCSL) maintains a database of state balance billing laws
- The Commonwealth Fund has a comprehensive comparison: https://www.commonwealthfund.org/publications/maps-and-interactives/2021/feb/state-balance-billing-protections
- Each state's insurance commissioner website lists patient protections

The JSON structure makes it trivial to add new states — just append entries to `state_laws.json` and re-run the seed script.

---

## Component 7: CPT Code Explorer

### Purpose
A standalone search tool that lets anyone look up the fair price for any medical procedure by name or CPT code. This serves three functions:
1. **User utility**: Patients can research prices before a procedure, not just after
2. **Demo prop**: During Q&A, a judge asks "what about an MRI?" and you type it in live — instant credibility
3. **Data showcase**: Demonstrates the depth of the CMS pricing database powering the app

### Implementation (`backend/routers/explore.py`)

```python
from fastapi import APIRouter, HTTPException, Query
import sqlite3
from config import DATABASE_PATH

router = APIRouter()
DB_PATH = DATABASE_PATH


@router.get("/search-cpt")
async def search_cpt(
    q: str = Query(..., min_length=2, description="Search query for procedure name or CPT code"),
    limit: int = Query(20, ge=1, le=50, description="Max results to return")
):
    """Search CPT codes by description keyword or code prefix."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Check if query looks like a CPT code (starts with digits)
    if q.strip().isdigit() or (len(q) == 5 and q[0].isdigit()):
        # Search by code prefix
        cursor = conn.execute(
            "SELECT cpt_code, description, non_facility_price, facility_price FROM medicare_rates WHERE cpt_code LIKE ? LIMIT ?",
            (f"{q.strip()}%", limit)
        )
    else:
        # Search by description keywords (AND logic: all words must match)
        words = q.strip().split()
        conditions = " AND ".join(["description LIKE ?" for _ in words])
        params = [f"%{word}%" for word in words]
        cursor = conn.execute(
            f"SELECT cpt_code, description, non_facility_price, facility_price FROM medicare_rates WHERE {conditions} ORDER BY non_facility_price DESC LIMIT ?",
            params + [limit]
        )

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        nf_price = row["non_facility_price"]
        f_price = row["facility_price"]
        base_price = nf_price or f_price or 0

        results.append({
            "cpt_code": row["cpt_code"],
            "description": row["description"],
            "medicare_non_facility": nf_price,
            "medicare_facility": f_price,
            "fair_price_range": {
                "low": round(base_price * 1.5, 2) if base_price else None,
                "mid": round(base_price * 2.0, 2) if base_price else None,
                "high": round(base_price * 2.5, 2) if base_price else None,
            }
        })

    return {
        "query": q,
        "results": results,
        "total_results": len(results)
    }


@router.get("/state-laws/{state_code}")
async def get_state_laws_endpoint(state_code: str):
    """Return all billing protection laws for a state plus federal laws."""
    from services.state_laws import get_state_laws
    result = get_state_laws(state_code)
    if result is None:
        raise HTTPException(status_code=404, detail=f"State code '{state_code}' not recognized")
    return result
```

### Search Behavior Details

**Query parsing**:
- If the query is numeric or looks like a CPT code (e.g., "99214", "8005"), search by code prefix
- If the query is text (e.g., "MRI knee"), split into words and require ALL words to match the description (AND logic)
- Results ordered by price descending (most expensive first — these are the ones people care about)

**Performance**: SQLite `LIKE` with `%word%` is fine for the CMS dataset (~13,000 rows). No need for full-text search at this scale.

**Popular searches to pre-populate** (clickable pills in the UI):
| Label | Query | Why it's interesting |
|-------|-------|---------------------|
| MRI | `MRI` | ~$200-600 Medicare rate, often billed at $2,000+ — dramatic overcharge |
| X-Ray | `x-ray` | Common, cheap ($20-50 Medicare), often marked up 5-10x |
| Blood Work | `blood` | Huge variety, some panels overcharged dramatically |
| Office Visit | `office visit` | The E/M levels (99211-99215) are the most common upcoding target |
| Physical Therapy | `physical therapy` | Multiple codes per session, common source of billing confusion |
| Colonoscopy | `colonoscopy` | Expensive procedure with facility fees — great for showing full cost breakdown |
| CT Scan | `CT scan` | High-value imaging, often balance-billed |
| Emergency Room | `emergency` | ER visit levels show dramatic price variation |

---

## Sample Data & Demo Bills

### Sample Bill A: "ER Visit with Labs" (errors planted)
Create a realistic-looking bill image with these line items:
- Emergency Department Visit Level 4 (99284) — $1,800
- Comprehensive Metabolic Panel (80053) — $225
- Basic Metabolic Panel (80048) — $150 ← UNBUNDLING: this is a subset of CMP
- CBC with Differential (85025) — $95
- Urinalysis (81003) — $60
- IV Infusion, first hour (96365) — $450
- IV Infusion, first hour (96365) — $450 ← DUPLICATE
- Facility Fee — $800
- **Total: $4,030**

**Expected findings**: 1 duplicate ($450 savings), 1 unbundling ($150 savings), several overcharges (lab prices 5-10x Medicare). Total savings: ~$1,200+. This is the bill you demo with.

### Sample Bill B: "Routine Checkup" (overcharges only, no errors)
- Office Visit Level 4 (99214) — $350
- Lipid Panel (80061) — $180
- TSH (84443) — $120
- Venipuncture (36415) — $75
- **Total: $725**

**Expected findings**: No billing errors. Labs overpriced relative to Medicare (especially lipid panel). Total savings: ~$250. Shows the tool works for normal situations too.

### Sample Bill C: "Clean Bill" (everything fair)
- Office Visit Level 3 (99213) — $190
- Flu Vaccine (90688) — $35
- Vaccine Administration (90471) — $25
- **Total: $250**

**Expected findings**: All prices within fair range. No errors. Apollo says "Your bill looks fair!" This is critical — it proves the tool is honest and not designed to always scare people.

### How to Create Sample Bills
Use a graphic design tool (Canva, Figma) or generate them programmatically to look like real hospital bills. They should include:
- Hospital/clinic name and address at the top
- Patient info (use fake names)
- Date of service
- Itemized charges with descriptions (CPT codes optional — tests the inference)
- Subtotals, insurance payments, patient balance
- Make them look slightly messy/clinical — not too polished, like a real bill

---

## Environment Variables & Configuration

### `.env` file (backend)
```
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_PATH=backend/db/pricing.db
ALLOWED_ORIGINS=http://localhost:5173,https://apollo-app.vercel.app
PORT=8000
```

### `.env` file (frontend)
```
VITE_API_URL=http://localhost:8000/api
```

### Gemini API Setup
1. Go to https://aistudio.google.com/apikey
2. Create a new API key
3. The free tier provides sufficient quota for a hackathon (15 RPM for Gemini 2.5 Pro)
4. No billing account needed for the free tier

---

## Pydantic Models (`backend/models/schemas.py`)

```python
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class Severity(str, Enum):
    fair = "fair"
    moderate = "moderate"
    high = "high"
    critical = "critical"
    unknown = "unknown"

class Provider(BaseModel):
    name: str
    address: Optional[str] = None
    npi: Optional[str] = None
    phone: Optional[str] = None

class Patient(BaseModel):
    name: Optional[str] = None
    account_number: Optional[str] = None
    date_of_service: Optional[str] = None
    insurance: Optional[str] = None

class LineItem(BaseModel):
    id: int
    description: str
    cpt_code: str
    cpt_inferred: bool = False
    quantity: int = 1
    unit_charge: float
    total_charge: float
    date: Optional[str] = None

class ParsedBill(BaseModel):
    provider: Provider
    patient: Patient
    line_items: list[LineItem]
    total_billed: float
    insurance_paid: Optional[float] = None
    adjustments: Optional[float] = None
    patient_responsibility: Optional[float] = None
    parsing_confidence: float

class BenchmarkResult(BaseModel):
    line_item_id: int
    cpt_code: str
    description: str
    charged: float
    medicare_rate: Optional[float] = None
    fair_price_low: Optional[float] = None
    fair_price_mid: Optional[float] = None
    fair_price_high: Optional[float] = None
    overcharge_ratio: Optional[float] = None
    potential_savings: float = 0.0
    severity: Severity = Severity.unknown
    note: Optional[str] = None

class AffectedItem(BaseModel):
    cpt_code: str
    description: str
    charge: Optional[float] = None

class BillingError(BaseModel):
    id: int
    type: str
    severity: str
    confidence: float
    title: str
    description: str
    affected_items: list
    estimated_overcharge: Optional[float] = None
    regulation: str
    recommendation: str

class AnalysisSummary(BaseModel):
    total_billed: float
    estimated_fair_total: float
    total_potential_savings: float
    savings_from_overcharges: float
    savings_from_errors: float
    overall_confidence: float
    items_flagged: int
    items_fair: int
    errors_found: int

class AnalysisResponse(BaseModel):
    parsed_bill: ParsedBill
    benchmarks: list[BenchmarkResult]
    errors: list[BillingError]
    dispute_letter: str
    state_laws: list["StateLaw"]
    federal_laws: list["StateLaw"]
    summary: AnalysisSummary

class StateLaw(BaseModel):
    law_name: str
    law_citation: str
    category: str                          # "balance_billing" | "surprise_billing" | "price_transparency" | "dispute_rights"
    summary: str
    applies_to: Optional[str] = None
    effective_date: Optional[str] = None
    url: Optional[str] = None

class StateLawsResponse(BaseModel):
    state_code: str
    state_name: str
    laws: list[StateLaw]
    federal_laws: list[StateLaw]

class CptSearchResult(BaseModel):
    cpt_code: str
    description: str
    medicare_non_facility: Optional[float] = None
    medicare_facility: Optional[float] = None
    fair_price_range: dict

class CptSearchResponse(BaseModel):
    query: str
    results: list[CptSearchResult]
    total_results: int

class GenerateLetterRequest(BaseModel):
    parsed_bill: ParsedBill
    selected_benchmarks: list[BenchmarkResult]
    selected_errors: list[BillingError]
    patient_state: str = "VA"
    additional_context: str = ""

class CptLookupResponse(BaseModel):
    cpt_code: str
    description: str
    medicare_non_facility: Optional[float] = None
    medicare_facility: Optional[float] = None
    fair_price_range: dict
```

---

## Build Timeline (12-Hour Hackathon)

| Hour | Task | Definition of Done |
|------|------|--------------------|
| 0-0.5 | **Project scaffolding** | React+Vite frontend and FastAPI backend both running locally. CORS configured. Test endpoint returns 200. |
| 0.5-1 | **Database setup** | CMS CSV loaded into SQLite. State laws JSON loaded. Can query `SELECT * FROM medicare_rates WHERE cpt_code = '99214'` and `SELECT * FROM state_laws WHERE state_code = 'VA'` and get results. CCI edits loaded. |
| 1-2.5 | **Bill parser (Gemini Vision)** | Can upload a bill image and get structured JSON back. Tested with 3 different bill formats. JSON schema validates. This is the riskiest piece — get it working first. |
| 2.5-4 | **Benchmarking engine** | Parsed line items → benchmarked results with severity ratings and savings amounts. Unit test with known CPT codes returns expected Medicare rates. |
| 4-5.5 | **Error detection** | Rule-based duplicate and unbundling detection working. AI-powered upcoding detection returning reasonable results. Tested with Sample Bill A (should find the planted errors). |
| 5.5-6 | **State Law Engine** | `GET /api/state-laws/VA` returns Virginia laws + federal laws. `get_laws_for_letter()` returns data ready for the letter generator. |
| 6-7 | **Dispute letter generator** | Gemini generates a professional letter with real data. Letter includes all flagged charges, errors, AND a "Your Rights" section citing state + federal statutes by name and citation. |
| 7-7.5 | **CPT Code Explorer backend** | `GET /api/search-cpt?q=MRI` returns matching procedures with fair prices. Search handles both keywords and CPT code prefixes. |
| 7.5-8 | **API orchestration** | Single POST /analyze endpoint chains all components including state law lookup. Returns the complete AnalysisResponse JSON with state_laws field. |
| 8-10 | **Frontend build** | Upload screen, loading animation, results dashboard with all sections (including State Law Panel). CPT Explorer tab working with debounced search. Charts rendering. Letter preview working. |
| 10-11 | **Sample bills & demo flow** | 3 sample bills created and working. "Try a sample" buttons load them instantly. Full flow works end-to-end. CPT Explorer has popular search pills. |
| 11-11.5 | **Polish** | Loading states. Error handling (graceful failures, not crashes). Animations on savings number. Mobile doesn't break. Deploy to Vercel + Railway. |
| 11.5-12 | **Demo rehearsal** | Run through the full demo 3 times. Time it. Have backup plan if live upload fails (use sample bill). Practice live CPT search for Q&A. |

### Critical Risk: Bill Parsing
If Gemini Vision struggles with certain bill formats, build a **manual correction fallback**: after parsing, show the extracted data in an editable table. The user can fix any misread values before running the analysis. This takes 30 minutes to build and saves you if parsing isn't perfect.

---

## Demo Script (3 Minutes)

**[0:00-0:20] The Hook**
"Raise your hand if you've ever gotten a medical bill you didn't fully understand. [pause] Now keep it up if you just paid it anyway. Studies show up to 80% of medical bills contain errors. Americans overpay by billions because the system is designed to be opaque. We built Apollo."

**[0:20-0:40] The Upload**
"Here's a bill from an ER visit." [click Sample A] "Apollo uses the Gemini API to read the bill — any format, any hospital — and extracts every line item with its billing code."

**[0:40-1:25] The Analysis**
[Results dashboard appears] "First, we benchmark every charge against real CMS Medicare pricing data — that's 13,000+ procedure codes. This lab panel? Charged $225. Medicare pays $14.49. Even at double the Medicare rate, this should be under $30."

"Second, we scan for billing errors. Apollo found a duplicate IV charge — $450 billed twice — and an unbundling issue: they billed both a Basic and Comprehensive Metabolic Panel. The BMP is a subset of the CMP. Per CMS coding rules, you can't bill both."

**[1:25-1:50] The Legal Teeth**
[Scroll to State Law Panel] "But Apollo doesn't just find problems — it tells you your rights. Because this patient is in Virginia, we pull Virginia Code § 38.2-3445.01, the Balance Billing Protection Act, plus the federal No Surprises Act. These aren't generic disclaimers — they're the exact statutes the billing department has to respond to."

**[1:50-2:15] The Action**
[Scroll to dispute letter] "All of this flows into a ready-to-send dispute letter: specific charges, Medicare fair prices, CCI coding rules, and a 'Your Rights' section citing Virginia law by statute number. One click to download."

**[2:15-2:35] The Savings + Explorer**
"Total billed: $4,030. Fair estimate: $2,400. Over $1,600 in savings." [Switch to Price Explorer tab] "And anyone can search our database — what does an MRI actually cost?" [type 'MRI', results appear instantly] "Medicare pays $198 for a knee MRI. If you're paying $2,000, now you know."

**[2:35-3:00] The Close**
"80% of medical bills have errors. Zero percent of patients have the tools to fight back. Until now. We're Apollo — powered by Gemini."

---

## Bonus Features (If Time Permits)

**Priority 1 — Share Card** (30 min)
Generate a shareable image: "Apollo found $1,600 in savings on my medical bill." Social proof format. Great for the pitch deck. Can be implemented as an HTML-to-canvas screenshot of the savings summary, or a simple server-side SVG template.

**Priority 2 — Historical Comparison** (1 hour)
Upload multiple bills over time and see trends: which providers overcharge most, which procedures are consistently inflated, total lifetime savings. Uses localStorage or a simple backend store to persist past analyses. Heavy data science angle — trend charts, provider rankings, category breakdowns.

**Priority 3 — Insurance Plan Optimizer** (2 hours)
Based on the user's billing history, model whether they'd save money on a different plan type (HMO vs. PPO vs. HDHP). Compare total out-of-pocket costs under different plan structures. This is a stretch goal but would be extremely impressive for the data science track.