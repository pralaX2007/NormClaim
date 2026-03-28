# NormClaim — GitHub Copilot Instructions

## Project Overview
NormClaim is an AI-powered clinical and administrative data normalisation engine for Indian SME hospitals. It converts unstructured hospital documents (PDF discharge summaries, lab reports, bills) into ABDM-compliant FHIR R4 Bundles and surfaces missed ICD-10 diagnoses with an estimated ₹ claim delta.

## Repository Layout
```
backend/              FastAPI (Python 3.11) — all API routes and services
  main.py             App entry point, CORS, routers
  routers/            documents · extract · fhir · reconcile
  services/           extractor (Gemini) · fhir_client · reconciler · pdf_parser · nlp_preprocessor
  models/             schemas.py (Pydantic) · database.py (SQLAlchemy/SQLite)
  data/               icd10_codes.json · drug_map.json · abbrev_map.json
  nlp_pipe/           extraction_pipeline.py (spaCy pre-processor)
  requirements.txt

web-dashboard/        Static HTML/CSS/JS front-end
  index.html          Document list + upload dropzone
  review.html         3-column view: original | entities | FHIR bundle
  reconcile.html      Claim gap report with ₹ delta table
  assets/             style.css · app.js

test-data/            Synthetic PDF generator (reportlab)
  generate.py         Produces discharge_complex.pdf · discharge_simple.pdf · lab_report.pdf · bill_undercoded.pdf
```

## Core Pipeline (4 stages)
1. **Ingest** — `POST /api/documents` stores the uploaded PDF.
2. **Extract** — `POST /api/extract/{id}` calls Gemini 1.5 Flash via `services/extractor.py` and returns an `ExtractionResult`.
3. **FHIR Map** — `POST /api/fhir/{id}` proxies the extraction to the HAPI FHIR Java microservice and returns a FHIR R4 Bundle.
4. **Reconcile** — `POST /api/reconcile/{id}` runs the ICD-10 diff engine and returns a `ReconciliationReport` with ₹ delta.

## Key Data Models (Pydantic — `models/schemas.py`)
- `PatientInfo` — name, age, sex, abha_id
- `Diagnosis` — text, icd10_code, is_primary, confidence
- `ExtractionResult` — patient, encounter, diagnoses, procedures, medications, billed_codes
- `ReconciliationReport` — matched, missed (with estimated_value_inr each), estimated_claim_delta_inr, confidence

## Tech Stack
- **Backend**: FastAPI · Python 3.11 · SQLite (SQLAlchemy) · pdfplumber · rapidfuzz
- **AI**: Gemini 1.5 Flash via `google-genai` SDK (`from google import genai`)
- **FHIR**: HAPI FHIR R4 Java Spring Boot microservice on port 8001
- **NLP**: spaCy `en_core_web_sm` + medspaCy for negation detection
- **Frontend**: Vanilla HTML/CSS/JS

## Coding Conventions
- Python: type-annotated, async/await for all I/O, Pydantic models for all request/response bodies.
- Use `google.genai` (package: `google-genai`) — NOT the older `google.generativeai` package.
- ICD-10 codes are validated/fuzzy-corrected via `rapidfuzz` against `data/icd10_codes.json`.
- INR claim values are estimated using `DRG_CLAIM_TABLE` in `services/reconciler.py`.
- All endpoints follow the pattern: read doc from storage → call service → persist result → return Pydantic model.
- Document state is stored in the SQLite DB via SQLAlchemy (`models/database.py`).

## Environment Variables
```
GEMINI_API_KEY       # Required — Gemini 1.5 Flash API key (free tier: 1,500 req/day)
FHIR_SERVICE_URL     # http://localhost:8001/fhir/bundle
BACKEND_URL          # http://localhost:8000
```

## Running Locally
```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Web dashboard
cd web-dashboard && python -m http.server 3000

# Generate test PDFs
pip install reportlab && python test-data/generate.py
```

## Domain Context
- Target users: billing clerks and RCM managers at Indian SME hospitals.
- AB-PMJAY (Ayushman Bharat) and ABDM-FHIR R4 compliance are mandatory from 2026.
- The reconciliation ₹ delta is based on approximate HBP (Health Benefit Package) rates.
- ICD-10 codes follow the WHO / Indian MoHFW classification.
- ABHA IDs are 14-digit identifiers issued by ABDM (Ayushman Bharat Digital Mission).
