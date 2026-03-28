# GitHub Copilot Instructions for NormClaim

## Project Overview
NormClaim is an **AI-powered Clinical & Administrative Data Normalization Engine** for Indian SME hospitals.  
It extracts clinical entities (diagnoses, procedures, medications) from PDF hospital documents, maps them to ICD-10 codes, generates ABDM-compliant FHIR R4 bundles, and produces a claim-gap reconciliation report showing missed diagnoses and estimated ₹ revenue delta.

## Repository Structure
- **`backend/`** — FastAPI (Python 3.11) orchestration service on port 8000
  - `main.py` — app entry point, all router registrations
  - `routers/` — REST endpoints: documents, extract, fhir, reconcile, review, feedback, validate
  - `services/` — business logic: extractor (Gemini AI), fhir_client, reconciler, pdf_parser, fhir_mapper
  - `models/` — Pydantic schemas and SQLAlchemy database models
  - `data/icd10_codes.json` — offline ICD-10 lookup table
- **`web-dashboard/`** — Static HTML/CSS/JS dashboard (index, review, reconcile pages)
- **`test-data/`** — Synthetic PDF test documents and generation script

## Key Technologies
- **AI extraction**: Google Gemini 1.5 Flash via `google-generativeai`; falls back to `pdfplumber` for text PDFs
- **FHIR mapping**: ABDM / NRCES FHIR R4 profiles; bundle built in Python (`fhir_mapper.py`) and optionally via HAPI FHIR Java service on port 8001
- **ICD-10 validation**: `rapidfuzz` fuzzy matching against local `data/icd10_codes.json`
- **Storage**: Supabase (production) with in-memory dict fallback for local dev
- **CORS**: fully open (`allow_origins=["*"]`) — tighten for production

## Coding Conventions
- Python: follow **PEP 8**, use **Black** (line length 88) and **Ruff** for linting
- All API request/response shapes are defined as **Pydantic v2** models in `models/schemas.py`
- Router functions should be `async def` and use FastAPI's dependency injection for shared resources
- Service functions should be standalone (no FastAPI imports) so they can be unit-tested independently
- Log with the named logger: `logger = logging.getLogger("normclaim")`
- ICD-10 codes are uppercase strings, e.g. `"E11.9"`, `"J18.9"`
- Monetary values are in **Indian Rupees (INR)**, field names suffixed `_inr`

## Environment Variables (`.env`)
```
GEMINI_API_KEY=          # Required — Google AI Studio free key
FHIR_SERVICE_URL=        # Optional — http://localhost:8001/fhir/bundle
SUPABASE_URL=            # Optional — Supabase project URL
SUPABASE_KEY=            # Optional — Supabase anon/service key
BACKEND_URL=             # Optional — http://localhost:8000
```

## Running Locally
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Swagger UI → http://localhost:8000/docs
```

## Common Tasks for Copilot
- **Adding a new router**: create `routers/<name>.py`, define `router = APIRouter(prefix="/api/<name>", tags=["<Name>"])`, import and register in `main.py`
- **Adding a new service**: create `services/<name>.py` with pure async functions; import from the corresponding router
- **Extending FHIR output**: edit `services/fhir_mapper.py`; add new resource builders following the existing `_build_*` pattern
- **Extending reconciliation**: edit `services/reconciler.py`; ICD-10 lookups go through `_lookup_icd10(code)` helper
