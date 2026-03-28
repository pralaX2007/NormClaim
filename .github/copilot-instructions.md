# GitHub Copilot Instructions for NormClaim

## Project Overview

NormClaim is an AI-powered Clinical & Administrative Data Normalization Engine for Indian SME hospitals. It solves revenue leakage (missed ICD-10 codes on discharge claims) and ABDM-FHIR R4 compliance simultaneously.

**Tagline:** _Every diagnosis. Every rupee._

Built by **Team Kaizen Unit** (Madhav Institute of Technology and Science, Gwalior) for the Jilo Health Hackathon × NJACK IIT Patna (PS-2).

---

## Repository Structure

```
NormClaim/
├── backend/          # FastAPI orchestration service (Python 3.11)
│   ├── main.py
│   ├── routers/      # documents, extract, fhir, reconcile, review, feedback, validate
│   ├── services/     # extractor (Gemini AI), fhir_client, reconciler, pdf_parser
│   ├── models/       # Pydantic schemas, database (Supabase)
│   ├── nlp_pipe/     # spaCy pre-processing pipeline
│   └── data/         # icd10_codes.json (local offline lookup)
│
├── web-dashboard/    # Static HTML/CSS/JS frontend
│   ├── index.html    # Document list + upload dropzone
│   ├── review.html   # 3-column: original | entities | FHIR
│   ├── reconcile.html# Claim gap report with ₹ delta table
│   └── assets/       # style.css, app.js
│
└── test-data/        # Synthetic test PDFs (generated with generate.py)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI · Python 3.11 · Uvicorn |
| AI Extraction | Google Gemini 1.5 Flash + pdfplumber |
| NLP Pre-processing | spaCy (en_core_web_sm) |
| FHIR Mapping | HAPI FHIR R4 · Spring Boot (Java 17) |
| ICD-10 Validation | rapidfuzz · local ICD-10 JSON (offline) |
| Storage | Supabase (PostgreSQL + Storage bucket) |
| Frontend | Static HTML/CSS/JS + fetch() |

---

## Core Pipeline (End-to-End)

```
PDF upload
  → pdfplumber text extraction (+ Gemini Vision OCR fallback)
  → spaCy NLP pre-processing (entity chunking, abbreviation expansion)
  → Gemini 1.5 Flash semantic extraction → structured JSON
  → rapidfuzz ICD-10 code validation/correction
  → HAPI FHIR Java service → ABDM-compliant FHIR R4 Bundle
  → ICD-10 diff engine → missed diagnoses + ₹ claim delta report
  → Human review layer → feedback loop
```

---

## Key Conventions

- **Python style:** PEP 8, Black formatter, type hints on all function signatures.
- **FastAPI routers:** Each domain has its own router in `backend/routers/`. All routes use `/api/` prefix.
- **Pydantic models:** All request/response schemas are in `backend/models/schemas.py`.
- **Supabase:** All database and storage calls go through the Python backend using `supabase-py`. Never call Supabase directly from the frontend.
- **Environment variables:** Never hardcode secrets. Use `.env` (not committed) with `.env.example` as the template. Key vars: `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `FHIR_SERVICE_URL`.
- **ICD-10 codes:** Validate and fuzzy-correct all codes against `backend/data/icd10_codes.json` using rapidfuzz before storing.
- **FHIR:** The Java HAPI FHIR service runs on port 8001. The Python backend proxies to it via `httpx`.
- **Currency:** Claim delta values are in Indian Rupees (INR, ₹). Estimated values come from `backend/data/icd10_codes.json` `estimated_value_inr` field.

---

## Supabase Schema

```sql
-- Documents table
documents (id uuid, filename text, storage_path text, uploaded_at timestamptz, status text, consent_obtained bool)

-- Extractions table
extractions (id uuid, document_id uuid, result_json jsonb, extracted_at timestamptz)

-- FHIR bundles table
fhir_bundles (id uuid, document_id uuid, bundle_json jsonb, generated_at timestamptz)

-- Reconciliations table
reconciliations (id uuid, document_id uuid, report_json jsonb, delta_inr numeric, reconciled_at timestamptz)

-- Human reviews table
human_reviews (id uuid, document_id uuid, reviewer_notes text, corrections_json jsonb, reviewed_at timestamptz)

-- Feedback table
feedback (id uuid, document_id uuid, was_correct bool, correction_type text, created_at timestamptz)
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents` | Upload PDF (multipart/form-data) |
| `GET` | `/api/documents` | List all documents + status |
| `POST` | `/api/extract/{id}` | Run Gemini AI extraction pipeline |
| `POST` | `/api/fhir/{id}` | Generate FHIR R4 Bundle via Java service |
| `POST` | `/api/reconcile/{id}` | Run ICD-10 diff + ₹ delta report |
| `POST` | `/api/review/{id}` | Submit human review corrections |
| `POST` | `/api/feedback/{id}` | Submit accuracy feedback |
| `POST` | `/api/validate/{id}` | Validate FHIR bundle against ABDM profiles |
| `GET` | `/health` | Health check |

---

## FHIR Resources (ABDM-aligned)

`Patient`, `Encounter`, `Condition` (ICD-10), `Observation` (LOINC), `MedicationRequest`, `Procedure`, `Claim`, `Bundle` — all profiled to ABDM FHIR R4 StructureDefinitions.

---

## Domain-Specific Terms

- **ICD-10:** International Classification of Diseases, 10th revision — used for billing diagnosis codes.
- **AB-PMJAY:** Ayushman Bharat Pradhan Mantri Jan Arogya Yojana — India's national health insurance scheme.
- **ABDM:** Ayushman Bharat Digital Mission — mandates FHIR R4 digital health records from 2026.
- **FHIR R4:** Fast Healthcare Interoperability Resources, Release 4 — the interoperability standard.
- **SME hospitals:** Small and Medium Enterprise hospitals in India (typically 30–200 beds).
- **TPA:** Third-Party Administrator — handles insurance claims processing.
- **DRG:** Diagnosis-Related Group — hospital reimbursement grouping.
- **Claim delta (₹):** Estimated revenue recoverable by adding missed diagnoses to the submitted claim.
