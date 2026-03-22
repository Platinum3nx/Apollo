# Apollo Product Requirements Document

## Product Summary

Apollo is a web application that helps patients review medical bills and identify charges that may deserve follow-up. A user uploads one or more bill images or PDFs, selects their state and facility type, and receives:

- structured bill line items
- pricing benchmarks based on public CMS datasets
- likely billing issues such as duplicates, unbundling, and suspicious charges
- state and federal patient-protection context
- a ready-to-edit dispute letter

Apollo is intended to reduce the effort required for a patient to understand a bill and take an informed next step.

## Problem Statement

Medical bills are difficult for most patients to audit. Charges are often presented in opaque language, CPT codes may be missing or unclear, and patients rarely have a practical way to compare billed amounts against reference pricing or spot common billing mistakes. Even when a patient suspects a problem, turning that suspicion into a clear written dispute is time-consuming.

Apollo addresses that gap by combining document understanding, public pricing data, billing-rule checks, and letter generation in a single workflow.

## Target Users

Primary user:
- Patients or family members reviewing a post-visit medical bill

Secondary users:
- Consumer advocates or support staff helping patients interpret a bill
- Demo reviewers evaluating the quality and completeness of the workflow

## Product Goals

- Make bill review accessible to a non-expert user
- Surface findings that are concrete, evidence-backed, and easy to understand
- Give the user an actionable output, not just an analysis
- Keep the experience fast enough for a live demo and practical for real use

## Non-Goals

- Replacing a licensed attorney, coder, or billing advocate
- Determining a patient's exact contracted insurance rate
- Adjudicating insurance coverage or benefits eligibility
- Automatically submitting disputes to providers or payers

## Core User Flow

1. The user uploads one or more PNG, JPG, or PDF bill files.
2. The user selects their state and whether the bill should be evaluated as facility or non-facility pricing.
3. Apollo extracts provider, patient, and line-item data from the uploaded documents.
4. Each line item is benchmarked against the pricing database.
5. Apollo runs deterministic billing checks and AI-assisted review for additional issues.
6. Apollo returns a summary dashboard with estimated savings, flagged items, legal context, and a dispute letter.
7. The user can copy, download, or regenerate the letter after selecting which issues to include.

## Functional Requirements

### 1. Bill Intake and Parsing

- Accept single-file and multi-file uploads
- Support common bill formats: PNG, JPG, JPEG, and PDF
- Extract or infer structured line items, including description, CPT code, quantity, and charge
- Return provider and patient metadata when present on the document

### 2. Pricing Benchmarking

- Compare each parsed line item against the local pricing database
- Support both facility and non-facility reference pricing
- Return a benchmark range and a midpoint-based savings estimate for each line item
- Mark lines as fair, moderate, high, critical, or unknown when pricing data is unavailable

### 3. Billing Error Detection

- Detect duplicate charges deterministically
- Detect unbundling against active CMS CCI edit pairs
- Use AI-assisted review to flag additional issues such as upcoding, unlikely combinations, or questionable charges
- Deduplicate overlapping findings and attach estimated overcharge values where possible

### 4. Legal Context

- Return state-specific patient-protection laws based on the selected state
- Include relevant federal protections alongside state laws
- Present legal context as supporting information for the user and for the generated dispute letter

### 5. Dispute Letter Generation

- Generate a plain-English dispute letter from the analysis results
- Allow the user to regenerate the letter using a selected subset of findings
- Allow the user to provide edited draft guidance when regenerating
- Support copy-to-clipboard and PDF export from the frontend

### 6. CPT Price Explorer

- Provide a standalone CPT lookup experience
- Support direct CPT-code lookup and keyword search
- Return both facility and non-facility Medicare reference pricing when available

## User Experience Requirements

- The upload flow should be simple enough for a first-time user to complete without instructions
- The results view should separate summary, pricing, billing errors, legal context, and the dispute letter into readable sections
- The product should clearly state that results are estimates and should be reviewed before use
- The interface should work across desktop and mobile layouts

## Data and Decision Logic

Apollo relies on local copies of the following datasets:

- CMS Physician Fee Schedule
- Clinical Laboratory Fee Schedule data, where available
- CMS Correct Coding Initiative edit pairs
- State-law reference data curated into JSON and loaded into SQLite

Pricing logic:

- Apollo derives a reference fair-price band from Medicare pricing
- The current UI presents low, mid, and high ranges, with the midpoint used for savings estimation
- Savings are calculated to avoid double counting when a line is both overpriced and affected by a billing error

## Technical Overview

Frontend:
- React 19
- Vite
- Tailwind CSS
- Axios and jsPDF

Backend:
- FastAPI
- SQLite
- Pydantic models

AI:
- Google Gemini API for bill parsing, AI-assisted auditing, and dispute-letter generation

Representative API surface:
- `POST /api/analyze`
- `POST /api/generate-letter`
- `GET /api/lookup/{cpt_code}`
- `GET /api/search-cpt`
- `GET /api/state-laws/{state_code}`

## Current Implementation Status

The repository currently implements:

- multi-file bill upload
- Gemini-backed bill parsing
- pricing lookups against the seeded SQLite database
- duplicate-charge and unbundling detection
- AI-assisted identification of additional billing concerns
- state and federal law retrieval
- editable dispute-letter generation and regeneration
- a standalone CPT Price Explorer

The application is already structured as a working end-to-end product rather than a static mockup.

## Constraints and Risks

- Poor scan quality or incomplete bills can reduce parsing accuracy
- Public benchmark pricing is a reference point, not a guarantee of what a provider should charge in every contract context
- Legal citations should be treated as supporting context, not individualized legal advice
- AI-dependent steps may occasionally fail; the system should degrade gracefully where deterministic fallbacks are available

## Repository Overview

```text
Apollo/
├── frontend/   # React client
├── backend/    # FastAPI API, services, models, and database tooling
├── scripts/    # Utility and smoke-test scripts
├── README.md
└── PRD.md
```
