# NormClaim

> **Every diagnosis. Every rupee.**

AI-Powered Clinical & Administrative Data Normalization Engine for Indian SME hospitals.

Built by **Team Kaizen Unit** for the [Jilo Health Hackathon × NJACK IIT Patna](https://hackathon.jilohealth.com) — Problem Statement PS-2.

---

## The Problem

Indian SME hospitals lose ₹12,000–40,000 per patient discharge in unclaimed diagnoses — not because the doctor didn't treat the conditions, but because billing clerks manually transcribe ICD-10 codes from discharge summaries and routinely miss comorbidities and secondary diagnoses. There is no intelligent normalization layer between clinical documents and payer claim fields.

**68%** of SME hospitals under-code claims due to manual entry. From 2026, all AB-PMJAY empanelled hospitals must also be ABDM-FHIR R4 compliant — a mandate that makes this problem simultaneously a revenue and compliance crisis.

---

## What NormClaim Does

```
PDF (discharge summary / lab report / bill)
        ↓
  AI Extraction  →  FHIR R4 Bundle  →  Claim Gap Report + ₹ Delta
```

1. **Ingest** — Upload any hospital document (PDF or scanned image)
2. **Extract** — Gemini 1.5 Flash reads the document and returns structured JSON: patient, diagnoses with ICD-10 codes, procedures, medications, billed codes
3. **Map** — HAPI FHIR Java service builds a valid ABDM-compliant FHIR R4 Bundle
4. **Reconcile** — ICD-10 diff engine compares extracted diagnoses against billed codes, surfaces missed diagnoses and estimates the ₹ claim delta

---

## Team Kaizen Unit

| Name | Role | College |
|------|------|---------|
| **Naitik Kanha** | Team Leader | Madhav Institute of Technology and Science, Gwalior |
| Sambhav Raj Onkar | Member | Madhav Institute of Technology and Science, Gwalior |
| Pratik Harsude | Member | Madhav Institute of Technology and Science, Gwalior |
| Pralakhy Kaushik | Member | Madhav Institute of Technology and Science, Gwalior |

---

## Repository Structure

```
normclaim/
├── backend/                        # FastAPI orchestration service (Python)
│   ├── main.py                     # App entry point, all routes
│   ├── routers/
│   │   ├── documents.py            # POST /api/documents  (upload)
│   │   ├── extract.py              # POST /api/extract/{id}
│   │   ├── fhir.py                 # POST /api/fhir/{id}
│   │   └── reconcile.py            # POST /api/reconcile/{id}
│   ├── services/
│   │   ├── extractor.py            # Gemini API + pdfplumber pipeline
│   │   ├── fhir_client.py          # HTTP client → Java FHIR service
│   │   ├── reconciler.py           # ICD-10 diff + ₹ delta engine
│   │   └── pdf_parser.py           # Text + image extraction from PDFs
│   ├── models/
│   │   ├── schemas.py              # Pydantic models (all I/O types)
│   │   └── database.py             # SQLAlchemy SQLite setup
│   ├── data/
│   │   └── icd10_codes.json        # Local ICD-10 lookup (offline)
│   └── requirements.txt
│
├── fhir-service/                   # HAPI FHIR Java Spring Boot microservice
│   ├── pom.xml
│   └── src/main/java/com/normclaim/fhir/
│       ├── FhirApplication.java
│       ├── controller/
│       │   └── FhirController.java # POST /fhir/bundle
│       └── service/
│           └── BundleBuilderService.java   # Builds FHIR R4 Bundle
│
├── android/                        # Android app (Java)
│   └── app/src/main/java/com/normclaim/
│       ├── MainActivity.java       # Document list + upload trigger
│       ├── UploadActivity.java     # File pick → upload → extract flow
│       ├── ResultActivity.java     # Entities tab + Claim Report tab
│       └── network/
│           └── ApiService.java     # Retrofit2 interface
│
├── web-dashboard/                  # Static HTML/CSS/JS dashboard
│   ├── index.html                  # Document list + upload dropzone
│   ├── review.html                 # 3-column: original | entities | FHIR
│   ├── reconcile.html              # Claim gap report with ₹ delta table
│   └── assets/
│       ├── style.css
│       └── app.js
│
├── test-data/                      # Synthetic test documents
│   ├── generate.py                 # Script to generate all PDFs
│   ├── discharge_complex.pdf       # 4 diagnoses, 1 billed — main demo doc
│   ├── discharge_simple.pdf        # Correctly coded — delta = ₹0
│   ├── lab_report.pdf              # 8 lab values → FHIR Observations
│   └── bill_undercoded.pdf         # Bill showing only J18.9
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│   Android App (Java)          Web Dashboard (HTML/JS)       │
│   MainActivity                index.html                    │
│   UploadActivity              review.html                   │
│   ResultActivity              reconcile.html                │
└──────────────┬──────────────────────────┬───────────────────┘
               │ Retrofit2                │ fetch()
               ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Backend  :8000  (Python)              │
│                                                             │
│  POST /api/documents     →  store uploaded PDF              │
│  POST /api/extract/{id}  →  run AI extraction pipeline      │
│  POST /api/fhir/{id}     →  proxy to FHIR Java service      │
│  POST /api/reconcile/{id}→  run ICD-10 diff + ₹ delta       │
│  GET  /api/documents     →  list all documents + status     │
└──────┬─────────────────────────────────┬────────────────────┘
       │                                 │ httpx
       ▼                                 ▼
┌──────────────────┐          ┌──────────────────────────────┐
│  Gemini 1.5 Flash│          │  HAPI FHIR Service  :8001    │
│  + pdfplumber    │          │  (Java Spring Boot)          │
│                  │          │                              │
│  Text/image →    │          │  POST /fhir/bundle           │
│  structured JSON │          │  → FHIR R4 Bundle JSON       │
└──────────────────┘          └──────────────────────────────┘
```

### FHIR Resources Generated

| Resource | Source | ABDM Profile |
|----------|--------|--------------|
| `Patient` | Discharge summary header | AbdmPatient |
| `Encounter` | Admission / discharge dates | AbdmEncounter |
| `Condition` | Diagnoses → ICD-10 coded | AbdmCondition |
| `Observation` | Lab report values → LOINC | AbdmObservation |
| `MedicationRequest` | Discharge medications | AbdmMedicationRequest |
| `Procedure` | Surgical / diagnostic procedures | AbdmProcedure |
| `Claim` | Bill / claim document | AbdmClaim |
| `Bundle` | Wraps all resources | AbdmDocumentBundle |

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend API | FastAPI · Python 3.11 | Async REST, auto OpenAPI docs, all ML libraries |
| AI Extraction | Gemini 1.5 Flash + pdfplumber | Multimodal (text + scanned images), 1,500 free req/day |
| FHIR Mapping | HAPI FHIR R4 · Spring Boot (Java) | Gold-standard FHIR library, R4 validation built-in |
| ICD-10 Validation | rapidfuzz · local ICD-10 JSON | No paid API, fuzzy-corrects LLM code outputs offline |
| Frontend | Android (Java, Retrofit2) + HTML/JS | Clerk on mobile, RCM manager on web dashboard |
| Storage | SQLite → PostgreSQL (prod) | Zero setup for demo, one-line config swap for production |

---

## Quickstart

### Prerequisites

- Python 3.11+
- Java 17+ and Maven 3.8+
- Android Studio (for Android app)
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free tier: 1,500 req/day)

### 1. Clone & configure

```bash
git clone https://github.com/Aethe-ui/NormClaim.git
cd NormClaim
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

### 2. Run with Docker Compose (recommended)

```bash
docker compose up --build
```

Services will be available at:
- Backend API: `http://localhost:8000`
- FHIR Service: `http://localhost:8001`
- Web Dashboard: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

### 3. Run manually

**Backend (Python):**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**FHIR Service (Java):**
```bash
cd fhir-service
mvn spring-boot:run
# Starts on port 8001
```

**Web Dashboard:**
```bash
cd web-dashboard
# Open index.html directly in browser, or serve with:
python -m http.server 3000
```

**Android App:**
```
Open android/ in Android Studio
Set BASE_URL in app/build.gradle to your machine's IP
Run on emulator (use http://10.0.2.2:8000) or physical device
```

### 4. Generate test data

```bash
pip install reportlab
python test-data/generate.py
# Creates 4 synthetic PDFs in test-data/
```

---

## API Reference

All endpoints are documented at `http://localhost:8000/docs` (Swagger UI).

### Upload a document
```http
POST /api/documents
Content-Type: multipart/form-data

file: <PDF file>

→ { "document_id": "uuid", "filename": "...", "status": "uploaded" }
```

### Run AI extraction
```http
POST /api/extract/{document_id}

→ {
    "document_id": "uuid",
    "patient": { "name": "Rajesh Kumar", "age": 58, "sex": "M", "abha_id": null },
    "encounter": { "admit_date": "2026-03-10", "discharge_date": "2026-03-14" },
    "diagnoses": [
      { "text": "Pneumonia", "icd10_code": "J18.9", "is_primary": true, "confidence": 0.95 },
      { "text": "Type 2 Diabetes", "icd10_code": "E11.9", "is_primary": false, "confidence": 0.91 }
    ],
    "billed_codes": ["J18.9"],
    ...
  }
```

### Generate FHIR bundle
```http
POST /api/fhir/{document_id}

→ {
    "resourceType": "Bundle",
    "type": "document",
    "meta": { "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle"] },
    "entry": [ ... Patient, Encounter, Condition, Claim resources ... ]
  }
```

### Run reconciliation
```http
POST /api/reconcile/{document_id}

→ {
    "matched": [{ "icd10_code": "J18.9", "description": "Pneumonia", "status": "matched" }],
    "missed":  [
      { "icd10_code": "E11.9", "description": "Type 2 diabetes mellitus", "status": "missed", "estimated_value_inr": 6950 },
      { "icd10_code": "I10",   "description": "Essential hypertension",   "status": "missed", "estimated_value_inr": 4150 },
      { "icd10_code": "N18.3", "description": "Chronic kidney disease",   "status": "missed", "estimated_value_inr": 6400 }
    ],
    "estimated_claim_delta_inr": 17500,
    "confidence": 0.92
  }
```

---

## Demo Walkthrough

The prototype ships with a synthetic discharge summary (`test-data/discharge_complex.pdf`) designed to demonstrate the full pipeline:

**Patient:** Rajesh Kumar, 58M  
**Admitted for:** Pneumonia  
**Comorbidities documented:** Type 2 Diabetes (E11.9), Essential Hypertension (I10), Chronic Kidney Disease Stage 3 (N18.3)  
**Original bill codes:** J18.9 only

**After NormClaim:**
- 4 diagnoses extracted, all ICD-10 validated
- FHIR R4 Bundle with 8 resource types generated
- 3 missed diagnoses surfaced in reconciliation report
- Estimated claim delta: **₹14,200 – ₹17,500**

---

## Supported Document Types

| Type | What's extracted | FHIR output |
|------|-----------------|-------------|
| Discharge summary | Patient, diagnoses, procedures, medications, dates | Patient + Encounter + Condition + MedicationRequest + Claim |
| Lab report | Test names, values, units, reference ranges | Observation resources |
| Bill / claim | Billed codes, amounts, procedure codes | Claim resource (used as baseline for reconciliation) |
| Scanned image PDF | All of the above via Gemini Vision multimodal | Same as above |

---

## Environment Variables

```bash
# .env
GEMINI_API_KEY=your_gemini_api_key_here     # Required — get free at aistudio.google.com
FHIR_SERVICE_URL=http://localhost:8001/fhir/bundle
BACKEND_URL=http://localhost:8000
```

Never commit `.env` to version control. A `.env.example` with placeholder values is provided.

---

## Roadmap

### Phase 1 — Hackathon MVP (current)
- [x] 4-layer pipeline (ingest → extract → FHIR map → reconcile)
- [x] ABDM-aligned FHIR R4 Bundle generation
- [x] ICD-10 gap analysis with ₹ delta
- [x] Android app (Java) + web dashboard
- [x] Offline-capable demo with pre-cached results

### Phase 2 — Pilot (3 months)
- [ ] Deploy at 2–3 SME hospitals in Tier 2 cities
- [ ] Test with real discharge summaries
- [ ] Measure actual ₹ recovered per hospital per month
- [ ] Add Hindi document support via Gemini multimodal

### Phase 3 — Product (6–12 months)
- [ ] ABDM sandbox API certification
- [ ] SaaS pricing: ₹5,000–15,000 per hospital per month
- [ ] TPA and insurer API direct integrations
- [ ] Batch processing for historical document backfill
- [ ] PostgreSQL + S3 for production storage

---

## Hackathon

**Event:** Jilo Health Hackathon on AI/ML in Healthcare  
**Organizers:** Jilo Health × NJACK IIT Patna  
**Venue:** IIT Patna, Bihar, India  
**Problem Statement:** PS-2 — AI-Powered Clinical & Administrative Data Normalization Engine  
**Contact:** jilohackathon@gmail.com

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*NormClaim — Every diagnosis. Every rupee.*  
*Team Kaizen Unit · Madhav Institute of Technology and Science, Gwalior*
