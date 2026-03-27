# NormClaim — Code Audit Report

**Audited:** 2026-03-27  
**Auditor:** AI Technical Review  
**Codebase ref:** `backend/` directory (FastAPI Python)  
**Context source:** `NORMCLAIM_CONTEXT.md`, `NormClaim_Master_Build_Prompt.md`, `README.md`

---

## 1. What Has Been Built

### ✅ Backend Skeleton (FastAPI)
- `main.py` — FastAPI app with CORS, startup logging, `/health` endpoint, all 4 routers registered
- `routers/documents.py` — `POST /api/documents` (upload), `GET /api/documents` (list)
- `routers/extract.py` — `POST /api/extract/{id}`, `GET /api/extract/{id}`
- `routers/fhir.py` — `POST /api/fhir/{id}`, `GET /api/fhir/{id}`
- `routers/reconcile.py` — `POST /api/reconcile/{id}`, `GET /api/reconcile/{id}`

### ✅ Data Models (`models/schemas.py`)
All Pydantic models are defined and match the spec:
`PatientInfo`, `EncounterInfo`, `Diagnosis`, `Procedure`, `Medication`, `ExtractionResult`,
`ReconciliationItem`, `ReconciliationReport`, `SpacyPreprocessResult`, `CorrectionItem`,
`HumanReview`, `FeedbackItem`

### ✅ Database Models (`models/database.py`)
SQLAlchemy models defined for `documents`, `extractions`, `reports` tables (SQLite). Tables are created at module load.

### ✅ PDF Parser (`services/pdf_parser.py`)
- `extract_text_from_pdf()` — pdfplumber-based text extraction from digital PDFs
- `pdf_to_base64_image()` — pdf2image fallback for scanned documents
- Properly handles both digital and scanned PDFs

### ✅ AI Extraction Service — Core (`services/extractor.py`, first half)
- Gemini API call using `google.genai` SDK
- Structured JSON prompt with strict schema definition
- Exponential backoff retry logic (3 attempts, 2/4/8s delays)
- ICD-10 fuzzy validation via `rapidfuzz` — corrects Gemini hallucinated codes against local lookup
- Scanned PDF fallback path (base64 image prompt)
- JSON extraction from markdown code fences (Gemini sometimes wraps output)

### ✅ FHIR HTTP Client (`services/fhir_client.py`)
- `generate_fhir_bundle()` — proxies `ExtractionResult` to Java HAPI FHIR service via httpx
- `check_fhir_health()` — health probe before sending data
- Async, uses `httpx.AsyncClient` with 30s timeout

### ✅ Reconciliation Engine (`services/reconciler.py`)
- Set-based ICD-10 diff: matched / missed / extra codes
- `DRG_CLAIM_TABLE` — approximate INR claim values by ICD-10 category (A–Z)
- `estimate_claim_value()` — category base rate + specificity bonus
- Confidence score averaged from extracted diagnosis confidence values
- Returns full `ReconciliationReport` with ₹ delta

### ✅ NLP Preprocessor (`services/nlp_preprocessor.py`)
- spaCy `en_core_web_sm` + medspaCy `ConTextComponent` for negation
- Abbreviation expansion (from `abbrev_map.json`)
- Section detection (complaint, history, diagnosis, medications, investigations, etc.)
- Negation detection (medspaCy + regex patterns for Indian clinical shorthand)
- Script detection (Roman / Devanagari / Mixed)

### ✅ NLP Extraction Pipeline (`nlp_pipe/extraction_pipeline.py`)
- Standalone spaCy-based text preprocessor
- Abbreviation expansion (hardcoded subset)
- Basic section and negation extraction

### ✅ Reference Data Files
- `data/icd10_codes.json` — ~90 common ICD-10 codes with descriptions (demo set)
- `data/drug_map.json` — ~60 Indian brand-to-generic drug name mappings
- `data/abbrev_map.json` — ~60 Indian clinical abbreviation expansions

### ✅ Test Data
- `test-data/generate.py` — comprehensive synthetic PDF generator using `reportlab` (4 document types: complex discharge, simple discharge, lab report, undercoded bill)

### ✅ Documentation
- `README.md` — full architecture diagram, API reference, quickstart, roadmap
- `NORMCLAIM_CONTEXT.md` — technical co-builder context
- `NormClaim_Master_Build_Prompt.md` — full scaffold prompt

---

## 2. What Is Broken / Not Working

### 🔴 CRITICAL — Extract Pipeline Never Calls Gemini

**File:** `routers/extract.py`  
The extract router calls `process_text(raw_text)` from `nlp_pipe/extraction_pipeline.py`.
This function only does spaCy preprocessing (abbreviation expansion, section detection, negation detection). **It never calls Gemini API.** It returns `{ expanded_text, sections, negated_spans }` — a `dict`, not an `ExtractionResult`.

Meanwhile, `services/extractor.py` contains the real Gemini extraction pipeline (`extract_from_document()`), but **it is never called** from any router.

Additionally, `routers/extract.py` decodes PDF bytes as UTF-8 text (`.decode("utf-8")`), but PDFs are binary files — this will produce garbage or crash on any real PDF.

**Impact:** Zero AI extraction occurs. The app cannot fulfil its core purpose.

---

### 🔴 CRITICAL — Duplicate & Conflicting Code in `services/extractor.py`

`services/extractor.py` contains **two entirely separate implementations** concatenated into one file without a separator:

1. **First half** — uses `google.genai` (new SDK), `GEMINI_MODEL = "gemini-2.5-flash-lite"`, standalone `extract_from_document()`. This is the correct implementation.
2. **Second half** — uses `import google.generativeai as palm`, `palm.chat(model="gemini-1.5-flash")`. The `palm.chat()` method **does not exist** in `google-generativeai==0.5.4`. It also uses `from backend.services.nlp_preprocessor import preprocess` — an absolute import that will fail when the app is run from the `backend/` directory.

Python will import only the first function named `extract`, `call_gemini`, etc. defined in the file. The second half silently overwrites variables. The app will crash at import time due to the `from backend.services...` absolute import.

---

### 🔴 CRITICAL — Document Storage: Supabase vs In-Memory Mismatch

**Files:** `routers/documents.py`, `routers/extract.py`

- `POST /api/documents` uploads the file to Supabase Storage and inserts metadata into Supabase DB. The **in-memory `DOCUMENTS` dict is never populated**.
- `POST /api/extract/{id}` checks `if document_id not in DOCUMENTS` and returns 404. Since `DOCUMENTS` is always empty (files go to Supabase), **every extraction attempt returns 404**.
- `GET /api/documents` reads from the in-memory `DOCUMENTS` dict, returning an empty list even though documents exist in Supabase.

The two storage systems are incompatible and unconnected.

---

### 🔴 CRITICAL — Supabase Credentials Block Startup

**File:** `main.py` (lines 65–67)

```python
if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("Supabase credentials missing.")
```

The app crashes at startup if `SUPABASE_URL` / `SUPABASE_KEY` are not set. There is no `.env.example` in the repo for contributors to reference, and Supabase was not mentioned as a required dependency in the original spec.

---

### 🟠 HIGH — `nlp_preprocessor.py` Import Errors

**File:** `services/nlp_preprocessor.py`

```python
from backend.data.abbrev_map import abbrev_map
```

`abbrev_map.json` and `drug_map.json` are JSON files, **not Python modules**. There is no `abbrev_map.py` or `drug_map.py`. This import will raise `ModuleNotFoundError` at startup.

Additionally, the path prefix `backend.` will fail when running `uvicorn main:app` from inside the `backend/` directory.

---

### 🟠 HIGH — Broken Regex Patterns in `nlp_preprocessor.py`

The raw string patterns use double-escaped backslashes (e.g., `"\\b"`, `"\\s+"`, `"\\u0900-\\u097F"`, `"(\\w+)"`).

```python
pattern = re.compile(r"\\b" + re.escape(abbr) + r"\\b", re.IGNORECASE)
```

`\\b` in a raw string is a literal backslash + `b`, not a word boundary. The patterns will **never match**. The Devanagari script detection also uses `"[\\u0900-\\u097F]"` which won't match Devanagari characters (should be `r"[\u0900-\u097F]"`).

---

### 🟠 HIGH — `nlp_pipe/extraction_pipeline.py` Returns Wrong Type

**File:** `routers/extract.py` (line 24), `nlp_pipe/extraction_pipeline.py`

`process_text()` returns a plain dict `{ expanded_text, sections, negated_spans }`. The `GET /api/extract/{id}` endpoint has `response_model=ExtractionResult`. When the stored dict is returned, Pydantic validation will fail because the dict has no `patient`, `encounter`, `diagnoses`, etc. fields.

---

### 🟠 HIGH — `requirements.txt` Missing Key Packages

The following packages are used in code but **not listed** in `requirements.txt`:
- `supabase` — used in `main.py` and `routers/documents.py`
- `spacy` — used in `nlp_pipe/extraction_pipeline.py` and `services/nlp_preprocessor.py`
- `medspacy` — used in both NLP files
- `pdf2image` — used in `services/pdf_parser.py` (optional fallback, but should be listed)
- `google-genai` — the new SDK package (`from google import genai`) used in the first half of `services/extractor.py` — the listed `google-generativeai==0.5.4` is a different SDK

---

### 🟡 MEDIUM — SQLAlchemy Database Models Never Used

**File:** `models/database.py`

Three ORM models (`DocumentRecord`, `ExtractionRecord`, `ReportRecord`) are defined and tables are created. However, **no router uses the DB session** (`get_db()` is never called). All state is stored in in-memory dicts, meaning all data is lost on server restart.

---

### 🟡 MEDIUM — FHIR Router Will Always Return 503

**File:** `routers/fhir.py`

The router calls `check_fhir_health()` before generating a bundle. Since the Java HAPI FHIR microservice (`fhir-service/`) **does not exist in this repo**, the health check will always fail and return HTTP 503.

---

### 🟡 MEDIUM — `list_documents` Reads Wrong Source

**File:** `routers/documents.py`

`GET /api/documents` iterates over `DOCUMENTS` (always empty). It should query Supabase (or SQLAlchemy) to list persisted documents.

---

### 🟡 MEDIUM — Gemini SDK Version Mismatch

The `requirements.txt` lists `google-generativeai==0.5.4`, but `services/extractor.py` (first, working half) uses `from google import genai` which is the newer `google-genai` package. These are two different PyPI packages with incompatible APIs. The correct package for the new SDK is `google-genai`, not `google-generativeai`.

---

### 🟡 MEDIUM — Test Data PDFs Not Generated / Committed

`test-data/` contains only `generate.py`. The actual PDF files (`discharge_complex.pdf`, `discharge_simple.pdf`, `lab_report.pdf`, `bill_undercoded.pdf`) referenced in the README **are not in the repo**. The demo cannot run without running `generate.py` first.

---

### 🟡 MEDIUM — ICD-10 Lookup Is Demo-Only (~90 Codes)

`data/icd10_codes.json` contains only ~90 entries. The full ICD-10 CM catalog has ~70,000 codes. While the `rapidfuzz` validator in `extractor.py` corrects hallucinated codes, it can only correct to codes within this tiny lookup. This means most extracted diagnoses will be incorrectly described or corrected to the wrong code.

---

### 🟢 LOW — `@app.on_event("startup")` is Deprecated

FastAPI/Starlette deprecated `@app.on_event("startup")` in favour of `lifespan` context managers. This is non-breaking but will generate deprecation warnings in newer FastAPI versions.

---

### 🟢 LOW — CORS Wildcard in Production

`allow_origins=["*"]` is acceptable for a hackathon prototype but must be locked down to specific origins before any production deployment.

---

## 3. What Has Not Been Built

### ❌ Frontend — Web Dashboard (`web-dashboard/`)
Described in README and master build prompt:
- `index.html` — document list + upload dropzone
- `review.html` — 3-column view (original | extracted entities | FHIR bundle)
- `reconcile.html` — claim gap report with ₹ delta table
- `assets/style.css` and `assets/app.js`

**Status:** Directory does not exist in the repo.

---

### ❌ Android App (`android/`)
Described in README and master build prompt:
- `MainActivity.java` — document list + upload trigger
- `UploadActivity.java` — file pick → upload → extract flow
- `ResultActivity.java` — entities tab + claim report tab
- `network/ApiService.java` — Retrofit2 interface

**Status:** Directory does not exist in the repo.

---

### ❌ FHIR Java Microservice (`fhir-service/`)
Described in README and master build prompt:
- Spring Boot application with HAPI FHIR R4
- `POST /fhir/bundle` — builds FHIR R4 Bundle from extraction JSON
- ABDM-compliant profiles for Patient, Encounter, Condition, Observation, MedicationRequest, Procedure, Claim, Bundle

**Status:** Directory does not exist in the repo. The Python FHIR router will always return 503.

---

### ❌ Docker Compose (`docker-compose.yml`)
Referenced in README quickstart. Not present in repo.

---

### ❌ Environment Template (`.env.example`)
Referenced in README. Not present in repo. New contributors have no reference for required environment variables.

---

### ❌ Human Review / Correction Workflow
Schemas for `HumanReview` and `CorrectionItem` are defined in `schemas.py` but no router, service, or UI exists to handle them.

---

### ❌ Feedback Loop
`FeedbackItem` schema is defined but there is no feedback endpoint, storage, or learning mechanism.

---

### ❌ Hindi / Hinglish Support
Mentioned in roadmap and context. spaCy's `en_core_web_sm` model does not handle Hindi/Hinglish mixed text well. Gemini Vision is expected to handle this but the pipeline is not wired correctly. No transliteration or Hindi NER model is integrated.

---

### ❌ Supabase Storage Download / Retrieval
`POST /api/documents` uploads to Supabase Storage but there is no endpoint or service method to download the file back for extraction.

---

### ❌ ABHA ID Validation
`PatientInfo.abha_id` is extracted but never validated or looked up against the ABDM registry.

---

### ❌ AB-PMJAY Real Claim Rate Table
`DRG_CLAIM_TABLE` in `reconciler.py` uses placeholder values (`4500`, `6800`, etc.). Real AB-PMJAY HBP package rates by procedure/diagnosis are not integrated.

---

## 4. Architecture Inconsistencies

| Issue | Location | Impact |
|-------|----------|--------|
| File stored in Supabase, referenced by in-memory dict | documents.py ↔ extract.py | Extraction always 404s |
| SQLAlchemy models defined but never used | database.py | State lost on restart |
| Two incompatible extractors in one file | services/extractor.py | Import crash |
| NLP pipeline (no-AI) wired where AI extractor should be | routers/extract.py | No AI extraction occurs |
| FHIR service expected on :8001 but not in repo | routers/fhir.py | Always 503 |
| `google-generativeai` vs `google-genai` in requirements | requirements.txt | SDK import failure |
| JSON data files imported as Python modules | nlp_preprocessor.py | ModuleNotFoundError |

---

## 5. Further Planning & Recommendations

### Priority 1 — Make Core Pipeline Work (Hackathon Demo)

1. **Fix document storage**: Remove Supabase from documents router. Store file bytes in-memory `DOCUMENTS` dict (or use SQLite via SQLAlchemy). Supabase can be added later.
2. **Wire the real AI extractor**: In `routers/extract.py`, read bytes from storage, call `extract_from_document(file_bytes, document_id)` from `services/extractor.py` instead of `process_text()`.
3. **Fix `services/extractor.py`**: Remove the second half (old `google.generativeai` implementation). Keep only the `google.genai`-based implementation.
4. **Fix `requirements.txt`**: Add `google-genai`, `supabase`, `spacy`, `medspacy`. Remove `google-generativeai`.
5. **Fix `nlp_preprocessor.py`**: Load `abbrev_map.json` with `json.load()` instead of Python import. Fix double-escaped regex patterns.
6. **Remove Supabase startup crash**: Make Supabase optional (warn instead of raise) so the app starts without credentials for local dev.
7. **Generate test PDFs**: Run `python test-data/generate.py` and commit the PDFs.

### Priority 2 — Build Missing Layers

8. **Web Dashboard**: Build `index.html`, `review.html`, `reconcile.html` with vanilla JS `fetch()` calls to the API. This is the demo's face — essential for judging.
9. **FHIR Microservice**: Build the Java Spring Boot service or implement FHIR bundle generation directly in Python using the `fhir.resources` PyPI package to remove the Java dependency for the hackathon.
10. **`.env.example`**: Add this file with placeholders for `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `FHIR_SERVICE_URL`.

### Priority 3 — Quality & Completeness

11. **Expand ICD-10 lookup**: Replace the 90-code JSON with the full ICD-10 CM 2024 dataset (freely available from CMS.gov) for accurate reconciliation.
12. **Wire SQLAlchemy**: Replace in-memory dicts with SQLAlchemy calls so data persists across restarts.
13. **AB-PMJAY claim rates**: Integrate real HBP 3.0 package rates for accurate ₹ delta estimation.
14. **Docker Compose**: Add `docker-compose.yml` for one-command startup of backend + FHIR service.
15. **Android app**: Implement the 3-activity Retrofit2 app for the mobile demo track.

### Priority 4 — Post-Hackathon / Phase 2

16. **Hindi/Hinglish NLP**: Integrate IndicNLP or use Gemini multimodal for mixed-script documents.
17. **ABHA ID integration**: Validate ABHA IDs via ABDM sandbox API.
18. **Human review workflow**: Implement `POST /api/review/{id}` using the existing `HumanReview` schema.
19. **Feedback endpoint**: Implement `POST /api/feedback/{id}` using `FeedbackItem` schema for active learning loop.
20. **Security hardening**: Restrict CORS origins, add API key auth, validate file size/MIME type strictly.

---

## 6. Summary Scorecard

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI skeleton + routing | ✅ Done | All 4 routes registered |
| Pydantic schemas | ✅ Done | Complete and correct |
| PDF text extraction | ✅ Done | Both digital + scanned |
| AI extraction (Gemini) | ⚠️ Built, not wired | Not called from router |
| ICD-10 fuzzy validation | ✅ Done | Working in extractor.py |
| FHIR HTTP proxy | ✅ Done | Waiting on Java service |
| Reconciliation engine | ✅ Done | Correct logic, demo INR values |
| NLP preprocessor | ⚠️ Built, broken imports | Regex bugs, import errors |
| Document storage | ❌ Broken | Supabase ↔ in-memory mismatch |
| SQLAlchemy persistence | ❌ Not wired | Defined but unused |
| Web dashboard | ❌ Not built | — |
| Android app | ❌ Not built | — |
| FHIR Java microservice | ❌ Not built | — |
| Docker Compose | ❌ Not built | — |
| Test PDFs | ❌ Not generated | generate.py exists |
| `.env.example` | ❌ Missing | — |

**Overall: ~40% of the described system is present in the repo. The critical extraction pipeline has structural bugs that prevent end-to-end functionality. The frontend and FHIR service layers are entirely absent.**
