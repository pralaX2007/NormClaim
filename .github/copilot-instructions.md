# NormClaim — GitHub Copilot Instructions

## Project Overview
NormClaim is an AI-powered Clinical & Administrative Data Normalization Engine for Indian SME hospitals. It solves revenue leakage (missed ICD-10 codes) and ABDM-FHIR R4 compliance for AB-PMJAY empanelled hospitals.

**Team:** Kaizen Unit — Madhav Institute of Technology and Science, Gwalior  
**Hackathon:** Jilo Health Hackathon × NJACK IIT Patna (PS-2)

---

## Pipeline
```
PDF (discharge summary / lab report / bill)
        ↓
  pdfplumber + spaCy pre-processing
        ↓
  Gemini 1.5 Flash semantic extraction → structured JSON
        ↓
  HAPI FHIR Java service → ABDM-compliant FHIR R4 Bundle
        ↓
  ICD-10 diff engine → Claim Gap Report + ₹ Delta
```

---

## Repository Layout
- `backend/` — FastAPI (Python 3.11) orchestration service on port 8000
  - `main.py` — App entry point and route registration
  - `routers/` — `documents.py`, `extract.py`, `fhir.py`, `reconcile.py`
  - `services/` — `extractor.py` (Gemini), `fhir_client.py`, `reconciler.py`, `pdf_parser.py`
  - `models/` — `schemas.py` (Pydantic), `database.py` (SQLAlchemy + SQLite)
  - `nlp_pipe/` — spaCy pre-processing pipeline
  - `data/icd10_codes.json` — offline ICD-10 lookup
- `web-dashboard/` — Static HTML/CSS/JS dashboard (index, review, reconcile pages)
- `test-data/` — Synthetic PDF test documents + `generate.py`

---

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI · Python 3.11 · Uvicorn |
| AI Extraction | Gemini 1.5 Flash + pdfplumber + spaCy |
| FHIR Mapping | HAPI FHIR R4 · Spring Boot (Java 17) on port 8001 |
| ICD-10 Validation | rapidfuzz · local ICD-10 JSON (offline) |
| Frontend | HTML/CSS/JS web dashboard + Android (Java) |
| Storage | SQLite (dev) → Supabase (production) |

---

## Coding Conventions
- **Python:** Follow PEP 8; use type hints for all function signatures; Pydantic models for all I/O schemas in `backend/models/schemas.py`
- **FastAPI routes:** use `APIRouter`, keep business logic in `services/`, thin router handlers only
- **FHIR resources:** must conform to ABDM/NRCES FHIR R4 profiles (e.g. `https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle`)
- **ICD-10 codes:** always validate against `data/icd10_codes.json` using `rapidfuzz` for fuzzy correction
- **Error handling:** return structured JSON error responses; use FastAPI `HTTPException`
- **Environment variables:** never hardcode secrets; read from `.env` via `python-dotenv`; required vars: `GEMINI_API_KEY`, `FHIR_SERVICE_URL`, `BACKEND_URL`

---

## Key Domain Concepts
- **ICD-10 codes:** International Classification of Diseases, 10th revision; used for diagnosis billing
- **FHIR R4:** HL7 Fast Healthcare Interoperability Resources standard, version R4
- **ABDM:** Ayushman Bharat Digital Mission — India's national health stack
- **AB-PMJAY:** Ayushman Bharat Pradhan Mantri Jan Arogya Yojana — India's public health insurance scheme
- **Claim delta (₹):** estimated revenue recovered by adding missed diagnoses to a claim
- **Comorbidity:** secondary condition present alongside primary diagnosis, often missed in manual billing

---

## API Endpoints (Backend)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents` | Upload a PDF document |
| `GET` | `/api/documents` | List all documents with status |
| `POST` | `/api/extract/{id}` | Run AI extraction pipeline |
| `POST` | `/api/fhir/{id}` | Generate FHIR R4 Bundle |
| `POST` | `/api/reconcile/{id}` | Run ICD-10 diff + ₹ delta |

---

## Running Locally
```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# FHIR Service (Java)
cd fhir-service && mvn spring-boot:run   # port 8001

# Web Dashboard
cd web-dashboard && python -m http.server 3000
```
