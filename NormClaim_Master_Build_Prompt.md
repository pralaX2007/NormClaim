# NormClaim — Master Prototype Build Prompt
> Paste this entire prompt into any AI coding agent (Claude, Cursor, Gemini, GPT-4o) to scaffold the full working prototype.

---

## 0. WHO YOU ARE / WHAT YOU ARE BUILDING

You are building **NormClaim** — an AI-powered Clinical & Administrative Data Normalization Engine for Indian SME hospitals. This is a hackathon prototype for the Jilo Health Hackathon × NJACK IIT Patna (PS-2).

**Core value proposition:** A hospital billing clerk uploads a discharge summary PDF. NormClaim's AI extracts all clinical entities, maps them to FHIR R4 resources (ABDM-compliant), then runs a reconciliation engine that compares extracted diagnoses against billed ICD-10 codes — surfacing the ₹ claim gap the hospital left on the table.

**Do not build a toy or a mockup.** Every layer must be genuinely functional on real synthetic test data. No hardcoded responses anywhere in the pipeline.

---

## 1. REPOSITORY STRUCTURE

Scaffold the following monorepo structure immediately:

```
normclaim/
├── backend/                  # FastAPI orchestration service (Python)
│   ├── main.py
│   ├── routers/
│   │   ├── documents.py      # /api/documents  (upload)
│   │   ├── extract.py        # /api/extract    (AI extraction)
│   │   ├── fhir.py           # /api/fhir       (FHIR bundle)
│   │   └── reconcile.py      # /api/reconcile  (gap analysis)
│   ├── services/
│   │   ├── extractor.py      # Gemini API extraction logic
│   │   ├── fhir_client.py    # HTTP client to Java FHIR service
│   │   ├── reconciler.py     # ICD-10 diff + ₹ delta engine
│   │   └── pdf_parser.py     # pdfplumber text extraction
│   ├── models/
│   │   ├── schemas.py        # Pydantic models for all I/O
│   │   └── database.py       # SQLAlchemy SQLite setup
│   ├── data/
│   │   └── icd10_codes.json  # Local ICD-10 lookup table (generate this)
│   └── requirements.txt
│
├── fhir-service/             # HAPI FHIR Java Spring Boot microservice
│   ├── pom.xml
│   └── src/main/java/com/normclaim/fhir/
│       ├── FhirApplication.java
│       ├── controller/FhirController.java
│       └── service/BundleBuilderService.java
│
├── android/                  # Android app (Java)
│   └── app/src/main/java/com/normclaim/
│       ├── MainActivity.java
│       ├── UploadActivity.java
│       ├── ResultActivity.java
│       └── network/ApiService.java   # Retrofit2 interface
│
├── web-dashboard/            # Static HTML/CSS/JS dashboard
│   ├── index.html            # Document list view
│   ├── review.html           # 3-column review: original | extracted | FHIR
│   ├── reconcile.html        # Claim gap report with ₹ delta table
│   └── assets/
│       ├── style.css
│       └── app.js
│
├── test-data/                # Synthetic test PDFs
│   ├── discharge_complex.pdf       # Patient with 4 diagnoses, 1 billed
│   ├── discharge_simple.pdf        # Single diagnosis, correctly billed
│   ├── lab_report.pdf              # Lab report with 8 test values
│   └── bill_undercoded.pdf         # Bill showing only J18.9
│
├── docker-compose.yml        # Runs backend + fhir-service together
└── README.md
```

---

## 2. BACKEND — FastAPI (Python)

### 2.1 `requirements.txt`
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
pdfplumber==0.11.0
Pillow==10.3.0
google-generativeai==0.5.4
rapidfuzz==3.9.3
sqlalchemy==2.0.30
httpx==0.27.0
pydantic==2.7.1
python-dotenv==1.0.1
```

### 2.2 Data Models — `models/schemas.py`

Define these Pydantic models exactly:

```python
from pydantic import BaseModel
from typing import List, Optional

class PatientInfo(BaseModel):
    name: str
    age: Optional[int]
    sex: Optional[str]
    abha_id: Optional[str]

class EncounterInfo(BaseModel):
    admit_date: Optional[str]
    discharge_date: Optional[str]
    ward: Optional[str]
    los_days: Optional[int]

class Diagnosis(BaseModel):
    text: str
    icd10_code: str
    is_primary: bool
    confidence: float  # 0.0 – 1.0

class Procedure(BaseModel):
    text: str
    date: Optional[str]

class Medication(BaseModel):
    name: str
    dose: Optional[str]
    duration: Optional[str]

class ExtractionResult(BaseModel):
    document_id: str
    patient: PatientInfo
    encounter: EncounterInfo
    diagnoses: List[Diagnosis]
    procedures: List[Procedure]
    medications: List[Medication]
    billed_codes: List[str]  # ICD-10 codes found on the original bill
    raw_text_preview: str    # first 500 chars of extracted text

class ReconciliationItem(BaseModel):
    icd10_code: str
    description: str
    status: str        # "matched" | "missed" | "extra"
    estimated_value_inr: Optional[float]

class ReconciliationReport(BaseModel):
    document_id: str
    matched: List[ReconciliationItem]
    missed: List[ReconciliationItem]
    extra: List[ReconciliationItem]
    total_billed_codes: int
    total_extracted_codes: int
    estimated_claim_delta_inr: float
    confidence: float
```

### 2.3 PDF Parser — `services/pdf_parser.py`

```python
import pdfplumber
import io

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract raw text from a PDF file bytes object.
    Handles both digital PDFs (pdfplumber) and returns
    a preview string. For scanned PDFs (no text layer),
    returns an empty string so the caller can fall back
    to Gemini Vision.
    """
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def pdf_to_base64_image(file_bytes: bytes) -> str:
    """
    Convert first page of PDF to base64 PNG for Gemini Vision.
    Use when extract_text_from_pdf returns empty string (scanned doc).
    """
    import base64
    from PIL import Image
    # Convert using pdf2image if available, else use Pillow fallback
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=200)
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        # Return empty — caller will handle
        return ""
```

### 2.4 AI Extractor — `services/extractor.py`

This is the most critical service. Implement it fully:

```python
import os
import json
import google.generativeai as genai
from models.schemas import ExtractionResult, PatientInfo, EncounterInfo, Diagnosis, Procedure, Medication
from services.pdf_parser import extract_text_from_pdf, pdf_to_base64_image
from rapidfuzz import process, fuzz
import json as _json

# Load ICD-10 lookup at module level
with open("data/icd10_codes.json") as f:
    ICD10_LOOKUP: dict = _json.load(f)  # {"J18.9": "Pneumonia, unspecified", ...}

ICD10_CODES = list(ICD10_LOOKUP.keys())

EXTRACTION_SYSTEM_PROMPT = """
You are a clinical NLP engine specialized in Indian hospital documents.
Extract ALL structured data from the provided hospital document.

STRICT RULES:
1. Return ONLY valid JSON. No preamble, no markdown backticks, no explanation.
2. Extract EVERY diagnosis mentioned — primary AND secondary AND comorbidities.
3. For each diagnosis, provide the ICD-10 code. If uncertain, provide your best match.
4. For billed_codes: extract ONLY the codes that appear on the original bill/claim section.
5. If a field is not found, use null. Never guess patient names.
6. Confidence is your certainty that the ICD-10 code is correct (0.0 to 1.0).

Return this exact JSON schema:
{
  "patient": {
    "name": "string or null",
    "age": integer or null,
    "sex": "M" | "F" | "Other" | null,
    "abha_id": "string or null"
  },
  "encounter": {
    "admit_date": "YYYY-MM-DD or null",
    "discharge_date": "YYYY-MM-DD or null",
    "ward": "string or null",
    "los_days": integer or null
  },
  "diagnoses": [
    {
      "text": "full diagnosis name as written in document",
      "icd10_code": "X00.0",
      "is_primary": true | false,
      "confidence": 0.0 to 1.0
    }
  ],
  "procedures": [
    {"text": "procedure name", "date": "YYYY-MM-DD or null"}
  ],
  "medications": [
    {"name": "drug name", "dose": "dose string or null", "duration": "duration or null"}
  ],
  "billed_codes": ["X00.0", "Y11.1"]
}
"""

def validate_icd10_codes(diagnoses: list) -> list:
    """
    Use rapidfuzz to validate and correct ICD-10 codes returned by Gemini.
    If a code is not in the official lookup, find the closest match.
    """
    for d in diagnoses:
        code = d.get("icd10_code", "").strip().upper()
        if code not in ICD10_LOOKUP:
            # Try fuzzy match on code string
            match, score, _ = process.extractOne(code, ICD10_CODES, scorer=fuzz.ratio)
            if score > 70:
                d["icd10_code"] = match
            # else keep original — it may be a valid ABDM extension
    return diagnoses

def extract_from_document(file_bytes: bytes, document_id: str) -> ExtractionResult:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Step 1: Try text extraction
    raw_text = extract_text_from_pdf(file_bytes)

    # Step 2: Build prompt content
    if raw_text and len(raw_text) > 100:
        # Digital PDF — use text
        prompt_content = [
            EXTRACTION_SYSTEM_PROMPT,
            f"\n\nDOCUMENT TEXT:\n{raw_text[:8000]}"  # cap at 8K chars
        ]
    else:
        # Scanned PDF — use Vision
        b64_image = pdf_to_base64_image(file_bytes)
        if not b64_image:
            raise ValueError("Could not extract text or image from PDF")
        import base64
        prompt_content = [
            EXTRACTION_SYSTEM_PROMPT,
            "\n\nDOCUMENT IMAGE (scanned):",
            {"mime_type": "image/png", "data": base64.b64decode(b64_image)}
        ]

    # Step 3: Call Gemini
    response = model.generate_content(prompt_content)
    raw_json = response.text.strip()

    # Step 4: Parse and validate
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        # Try to extract JSON from within the response
        import re
        match = re.search(r'\{.*\}', raw_json, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Gemini returned non-JSON: {raw_json[:200]}")

    # Step 5: Validate ICD-10 codes
    data["diagnoses"] = validate_icd10_codes(data.get("diagnoses", []))

    # Step 6: Build ExtractionResult
    return ExtractionResult(
        document_id=document_id,
        patient=PatientInfo(**data.get("patient", {})),
        encounter=EncounterInfo(**data.get("encounter", {})),
        diagnoses=[Diagnosis(**d) for d in data.get("diagnoses", [])],
        procedures=[Procedure(**p) for p in data.get("procedures", [])],
        medications=[Medication(**m) for m in data.get("medications", [])],
        billed_codes=data.get("billed_codes", []),
        raw_text_preview=raw_text[:500] if raw_text else "[scanned image]"
    )
```

### 2.5 Reconciliation Engine — `services/reconciler.py`

```python
import json
from models.schemas import ExtractionResult, ReconciliationReport, ReconciliationItem

with open("data/icd10_codes.json") as f:
    ICD10_LOOKUP: dict = json.load(f)

# Approximate claim value per ICD-10 code category (INR)
# Based on AB-PMJAY package rate approximations — use as demo values
DRG_CLAIM_TABLE = {
    "A": 4500,   "B": 3800,   "C": 5200,   "D": 4100,
    "E": 6800,   "F": 7200,   "G": 5500,   "H": 4300,
    "I": 8500,   "J": 4200,   "K": 6100,   "L": 3900,
    "M": 4700,   "N": 6400,   "O": 7800,   "P": 5100,
    "Q": 4400,   "R": 3600,   "S": 5900,   "T": 4800,
    "U": 3500,   "V": 4100,   "W": 3700,   "X": 4000,
    "Y": 3800,   "Z": 2800,
}

def estimate_claim_value(icd10_code: str) -> float:
    """Estimate billable value of an ICD-10 code using category-level table."""
    if not icd10_code:
        return 0.0
    category = icd10_code[0].upper()
    base = DRG_CLAIM_TABLE.get(category, 4000)
    # Add variation based on code specificity
    specificity_bonus = len(icd10_code.replace(".", "")) * 150
    return float(base + specificity_bonus)

def reconcile(extraction: ExtractionResult) -> ReconciliationReport:
    extracted_codes = {d.icd10_code.upper() for d in extraction.diagnoses}
    billed_codes = {c.upper() for c in extraction.billed_codes}

    matched_codes = extracted_codes & billed_codes
    missed_codes = extracted_codes - billed_codes    # In doc, NOT on bill
    extra_codes = billed_codes - extracted_codes      # On bill, NOT in doc

    def build_item(code: str, status: str) -> ReconciliationItem:
        description = ICD10_LOOKUP.get(code, f"ICD-10: {code}")
        value = estimate_claim_value(code) if status == "missed" else None
        return ReconciliationItem(
            icd10_code=code,
            description=description,
            status=status,
            estimated_value_inr=value
        )

    matched = [build_item(c, "matched") for c in matched_codes]
    missed  = [build_item(c, "missed")  for c in missed_codes]
    extra   = [build_item(c, "extra")   for c in extra_codes]

    total_delta = sum(m.estimated_value_inr for m in missed if m.estimated_value_inr)

    # Confidence based on how many extracted diagnoses have high-confidence codes
    avg_confidence = (
        sum(d.confidence for d in extraction.diagnoses) / len(extraction.diagnoses)
        if extraction.diagnoses else 0.0
    )

    return ReconciliationReport(
        document_id=extraction.document_id,
        matched=matched,
        missed=missed,
        extra=extra,
        total_billed_codes=len(billed_codes),
        total_extracted_codes=len(extracted_codes),
        estimated_claim_delta_inr=round(total_delta, 2),
        confidence=round(avg_confidence, 3)
    )
```

### 2.6 Main FastAPI App — `main.py`

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid, os
from models.schemas import ExtractionResult, ReconciliationReport
from services.extractor import extract_from_document
from services.reconciler import reconcile

app = FastAPI(title="NormClaim API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for hackathon (replace with SQLite in next iteration)
DOCUMENTS: dict = {}       # document_id -> file_bytes
EXTRACTIONS: dict = {}     # document_id -> ExtractionResult
REPORTS: dict = {}         # document_id -> ReconciliationReport

@app.post("/api/documents", response_model=dict)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document. Returns document_id."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    doc_id = str(uuid.uuid4())
    DOCUMENTS[doc_id] = await file.read()
    return {"document_id": doc_id, "filename": file.filename, "status": "uploaded"}

@app.post("/api/extract/{document_id}", response_model=ExtractionResult)
async def extract_document(document_id: str):
    """Run AI extraction on an uploaded document."""
    if document_id not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found")
    result = extract_from_document(DOCUMENTS[document_id], document_id)
    EXTRACTIONS[document_id] = result
    return result

@app.get("/api/extract/{document_id}", response_model=ExtractionResult)
async def get_extraction(document_id: str):
    if document_id not in EXTRACTIONS:
        raise HTTPException(status_code=404, detail="Not extracted yet")
    return EXTRACTIONS[document_id]

@app.post("/api/reconcile/{document_id}", response_model=ReconciliationReport)
async def run_reconciliation(document_id: str):
    """Run reconciliation on an extracted document."""
    if document_id not in EXTRACTIONS:
        raise HTTPException(status_code=404, detail="Extract first: POST /api/extract/{id}")
    report = reconcile(EXTRACTIONS[document_id])
    REPORTS[document_id] = report
    return report

@app.get("/api/reconcile/{document_id}", response_model=ReconciliationReport)
async def get_report(document_id: str):
    if document_id not in REPORTS:
        raise HTTPException(status_code=404, detail="No report found")
    return REPORTS[document_id]

@app.get("/api/documents")
async def list_documents():
    return [{"document_id": k, "has_extraction": k in EXTRACTIONS, "has_report": k in REPORTS}
            for k in DOCUMENTS]

@app.get("/health")
async def health():
    return {"status": "ok", "service": "normclaim-backend"}
```

Run with: `uvicorn main:app --reload --port 8000`

---

## 3. FHIR SERVICE — Java Spring Boot (HAPI FHIR)

### 3.1 `pom.xml` — add these dependencies:
```xml
<dependency>
    <groupId>ca.uhn.hapi.fhir</groupId>
    <artifactId>hapi-fhir-base</artifactId>
    <version>7.0.0</version>
</dependency>
<dependency>
    <groupId>ca.uhn.hapi.fhir</groupId>
    <artifactId>hapi-fhir-structures-r4</artifactId>
    <version>7.0.0</version>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

### 3.2 Input DTO — `FhirInputDto.java`

```java
public class FhirInputDto {
    public PatientDto patient;
    public EncounterDto encounter;
    public List<DiagnosisDto> diagnoses;
    public List<MedicationDto> medications;
    public List<ProcedureDto> procedures;
    public String documentId;

    public static class PatientDto {
        public String name, sex, abhaId;
        public Integer age;
    }
    public static class EncounterDto {
        public String admitDate, dischargeDate, ward;
    }
    public static class DiagnosisDto {
        public String text, icd10Code;
        public boolean isPrimary;
    }
    public static class MedicationDto {
        public String name, dose, duration;
    }
    public static class ProcedureDto {
        public String text, date;
    }
}
```

### 3.3 Bundle Builder — `BundleBuilderService.java`

Build the following FHIR R4 resources inside a `Bundle` of type `document`:

**Patient resource:**
- `identifier`: system = `https://abha.abdm.gov.in`, value = `abhaId`
- `name`: family + given from patient name
- `gender`: map M→male, F→female
- `meta.profile`: `["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient"]`

**Encounter resource:**
- `status`: "finished"
- `class`: coding system `http://terminology.hl7.org/CodeSystem/v3-ActCode`, code "IMP"
- `period`: start = admitDate, end = dischargeDate
- `subject`: reference to Patient

**Condition resources** (one per diagnosis):
- `code.coding`: system = `http://hl7.org/fhir/sid/icd-10`, code = icd10Code, display = text
- `clinicalStatus`: `active`
- `verificationStatus`: `confirmed`
- `category`: `encounter-diagnosis`
- `subject`: reference to Patient
- `encounter`: reference to Encounter

**MedicationRequest resources** (one per medication):
- `status`: "active"
- `intent`: "order"
- `medicationCodeableConcept.text`: medication name
- `subject`: reference to Patient

**Claim resource:**
- `status`: "active"
- `type`: system `http://terminology.hl7.org/CodeSystem/claim-type`, code "institutional"
- `diagnosis`: array — one entry per Condition, with `diagnosisCodeableConcept` from ICD-10
- `patient`: reference to Patient

**Bundle:**
- `type`: "document"
- `timestamp`: current ISO datetime
- `meta.profile`: `["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle"]`
- Add all resources to `entry[]` as `BundleEntryComponent`

Use `FhirContext.forR4()` to serialize the bundle to JSON string.

### 3.4 Controller — `FhirController.java`

```java
@RestController
@RequestMapping("/fhir")
public class FhirController {

    @Autowired BundleBuilderService bundleBuilder;

    @PostMapping("/bundle")
    public ResponseEntity<String> generateBundle(@RequestBody FhirInputDto input) {
        try {
            String fhirJson = bundleBuilder.buildBundle(input);
            return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .body(fhirJson);
        } catch (Exception e) {
            return ResponseEntity.status(500).body("{\"error\": \"" + e.getMessage() + "\"}");
        }
    }

    @GetMapping("/health")
    public String health() { return "{\"status\": \"ok\", \"service\": \"normclaim-fhir\"}"; }
}
```

Run on port 8001. FastAPI backend calls `POST http://localhost:8001/fhir/bundle`.

Add a `fhir_client.py` in the Python backend:
```python
import httpx
from models.schemas import ExtractionResult

FHIR_SERVICE_URL = "http://localhost:8001/fhir/bundle"

async def generate_fhir_bundle(extraction: ExtractionResult) -> dict:
    payload = extraction.model_dump()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(FHIR_SERVICE_URL, json=payload)
        resp.raise_for_status()
        return resp.json()
```

---

## 4. WEB DASHBOARD — `web-dashboard/`

Build a **3-page static web dashboard** using HTML, CSS (no framework), and vanilla JS.

### Design direction:
- **Aesthetic:** Medical-grade dark professional. Deep navy (`#0A1628`) background, teal (`#028090`) primary, gold (`#F5A623`) for warning/missed items, red (`#E05C4B`) for missed codes.
- **Typography:** `DM Serif Display` for headings (Google Fonts), `DM Mono` for codes and JSON, `DM Sans` for body.
- **Feel:** Like a Bloomberg terminal crossed with a hospital EHR — dense, data-rich, no fluff.

### Page 1 — `index.html` — Document List

Layout: full-width sidebar (document list) + main panel.

Features:
- File upload dropzone (drag-and-drop + click): `POST /api/documents`
- Document list showing: filename, upload time, status badges (Uploaded / Extracted / Reconciled)
- Click a document → runs `POST /api/extract/{id}` → shows loading state → navigates to `review.html?id={id}`
- Auto-poll `/api/documents` every 5s to refresh list

### Page 2 — `review.html` — Extraction Review

Layout: 3-column equal-width panels separated by dividers.

**Panel 1 — Original Document:**
- Show `raw_text_preview` in a monospace scrollable box
- Show document ID and filename

**Panel 2 — AI Extracted Entities:**
- Patient info card (name, age, sex, ABHA ID)
- Encounter card (admit/discharge dates, ward, LOS)
- Diagnoses table: `ICD-10 Code | Description | Primary? | Confidence`
  - Color code confidence: green >0.8, amber 0.5–0.8, red <0.5
- Procedures list
- Medications list (name, dose, duration)
- Billed codes section: show existing billing codes in gray chips

**Panel 3 — FHIR Bundle:**
- "Generate FHIR Bundle" button → calls `POST /api/fhir/{id}` (add this endpoint to FastAPI that proxies to Java service)
- Shows formatted JSON with syntax highlighting (use a `<pre>` with class-based coloring)
- Download button for the FHIR JSON file

Bottom bar: "Run Reconciliation →" button → navigates to `reconcile.html?id={id}`

### Page 3 — `reconcile.html` — Claim Gap Report

This is the demo punchline page. Make it dramatic.

Layout: top stats bar + main table + bottom delta callout.

**Top stats bar (4 cards):**
- Total Extracted Diagnoses
- Total Billed Codes
- Missed Diagnoses (in red)
- Estimated Claim Delta ₹ (in gold, large font)

**Main reconciliation table:**
Columns: `Status | ICD-10 Code | Description | Est. Value (₹)`

Row styling:
- `matched` rows: dark green background, ✓ icon
- `missed` rows: dark red background, ✗ icon, gold ₹ value shown
- `extra` rows: amber background, ⚠ icon

**Bottom callout box:**
Large gold-bordered card:
```
Estimated Claim Delta:  ₹ XX,XXX
X diagnoses found in document but never billed.
All are billable under AB-PMJAY guidelines.
```

Add a "Download Report (PDF)" button that uses `window.print()` with a print stylesheet.
Add a "Back to Documents" link.

---

## 5. ANDROID APP — Java

Build 3 activities with proper Material Design (use `com.google.android.material:material:1.12.0`):

### Activity 1 — `MainActivity.java`
- App bar with "NormClaim" title and teal color
- RecyclerView showing list of uploaded documents (fetched from `GET /api/documents`)
- FloatingActionButton → opens file picker for PDF selection
- Swipe-to-refresh on the list

### Activity 2 — `UploadActivity.java`
- Triggered after PDF file pick
- Shows selected filename and file size
- "Upload & Extract" button:
  1. `POST /api/documents` (multipart) with file → gets `document_id`
  2. `POST /api/extract/{document_id}` → polls until complete
  3. Navigates to `ResultActivity` with `document_id` as Intent extra
- Progress bar during upload+extraction
- Error handling with Snackbar

### Activity 3 — `ResultActivity.java`
- Two tabs using TabLayout: "Entities" | "Claim Report"

**Entities tab:**
- CardViews for: Patient Info, Encounter Info
- RecyclerView for diagnoses (ICD-10 chip + description + confidence bar)
- RecyclerView for medications

**Claim Report tab:**
- Summary cards: matched / missed / delta ₹
- RecyclerView of reconciliation items (color coded: green matched, red missed)
- "Share Report" button → shares JSON summary as text

### Network — `ApiService.java` (Retrofit2 interface)
```java
public interface ApiService {
    @Multipart
    @POST("api/documents")
    Call<UploadResponse> uploadDocument(@Part MultipartBody.Part file);

    @POST("api/extract/{id}")
    Call<ExtractionResult> extractDocument(@Path("id") String documentId);

    @POST("api/reconcile/{id}")
    Call<ReconciliationReport> reconcile(@Path("id") String documentId);

    @GET("api/documents")
    Call<List<DocumentInfo>> listDocuments();
}
```

Base URL: `http://10.0.2.2:8000/` (Android emulator → localhost). Make it configurable via `BuildConfig`.

---

## 6. SYNTHETIC TEST DATA — `test-data/`

Generate 4 synthetic PDFs using Python (`reportlab` library). Each must be realistic enough that Gemini extracts meaningful entities:

### `discharge_complex.pdf` — The demo document
Patient: Rajesh Kumar, 58M. Admitted with pneumonia (J18.9).
Also has: Type 2 Diabetes (E11.9), Essential Hypertension (I10), Chronic Kidney Disease Stage 3 (N18.3).
Medications: Amoxicillin 500mg, Metformin 500mg, Amlodipine 5mg.
**Bill only shows: J18.9** — so reconciliation finds 3 missed diagnoses ≈ ₹14,200 delta.

### `discharge_simple.pdf` — Clean, correctly coded
Patient: Priya Sharma, 34F. Appendicitis (K37). Appendectomy performed.
Bill correctly shows K37. Expected: no missed codes, delta = ₹0.

### `lab_report.pdf` — Lab values document
Patient: Amit Singh, 45M.
Tests: HbA1c 8.2%, FBS 168 mg/dL, Creatinine 2.1 mg/dL, BP 145/92, eGFR 42.
Expected: maps to FHIR Observation resources.

### `bill_undercoded.pdf` — Just a bill
Shows: Patient name, bill number, diagnosis J18.9, amount ₹8,500.
Used to demonstrate what the original bill looks like.

Generate all 4 with this script: `python test-data/generate.py`

---

## 7. DATA — `data/icd10_codes.json`

Generate a `icd10_codes.json` file containing at minimum the following 60 common ICD-10 codes used in Indian hospitals, in this format:

```json
{
  "J18.9": "Pneumonia, unspecified",
  "E11.9": "Type 2 diabetes mellitus without complications",
  "I10":   "Essential (primary) hypertension",
  "N18.3": "Chronic kidney disease, stage 3",
  "K37":   "Unspecified appendicitis",
  "I21.9": "Acute myocardial infarction, unspecified",
  "J44.1": "Chronic obstructive pulmonary disease with acute exacerbation",
  "A09":   "Gastroenteritis and colitis of unspecified origin",
  "B34.9": "Viral infection, unspecified",
  "K29.7": "Gastritis, unspecified",
  "M54.5": "Low back pain",
  "J06.9": "Acute upper respiratory infection, unspecified",
  "R51":   "Headache",
  "K92.1": "Melena",
  "N39.0": "Urinary tract infection, site not specified",
  "I50.9": "Heart failure, unspecified",
  "E78.5": "Hyperlipidemia, unspecified",
  "K80.20":"Calculus of gallbladder without cholecystitis, without obstruction",
  "S72.00":"Fracture of femoral neck, closed",
  "C34.90":"Malignant neoplasm of bronchus or lung, unspecified"
}
```
Add 40 more common codes covering: infections (A-B), neoplasms (C), endocrine (E), neurological (G), cardiovascular (I), respiratory (J), digestive (K), musculoskeletal (M), genitourinary (N), perinatal (P), injuries (S-T).

---

## 8. DOCKER COMPOSE — `docker-compose.yml`

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - FHIR_SERVICE_URL=http://fhir-service:8001/fhir/bundle
    depends_on:
      - fhir-service
    volumes:
      - ./test-data:/app/test-data

  fhir-service:
    build: ./fhir-service
    ports:
      - "8001:8001"

  web-dashboard:
    image: nginx:alpine
    ports:
      - "3000:80"
    volumes:
      - ./web-dashboard:/usr/share/nginx/html
```

---

## 9. `.env` FILE (create this, never commit)

```
GEMINI_API_KEY=your_gemini_api_key_here
FHIR_SERVICE_URL=http://localhost:8001/fhir/bundle
BACKEND_URL=http://localhost:8000
```

Get Gemini API key free at: https://aistudio.google.com/app/apikey
Free tier: 1,500 requests/day — sufficient for hackathon.

---

## 10. BUILD ORDER (follow exactly)

Build in this sequence. Do NOT skip ahead:

1. **Generate `data/icd10_codes.json`** — needed by everything else
2. **Generate `test-data/` PDFs** using reportlab — needed for testing
3. **Build `backend/` FastAPI** — models → pdf_parser → extractor → reconciler → main
4. **Test backend alone**: `uvicorn main:app --reload`, upload `discharge_complex.pdf`, verify extraction JSON
5. **Build `fhir-service/` Java** — BundleBuilderService → FhirController → test with curl
6. **Wire backend ↔ fhir-service** via `fhir_client.py`, add `/api/fhir/{id}` endpoint to FastAPI
7. **Build `web-dashboard/`** — index.html → review.html → reconcile.html
8. **End-to-end test**: upload PDF via web UI → extract → FHIR → reconcile → see ₹ delta
9. **Build Android app** — MainActivity → UploadActivity → ResultActivity
10. **Docker Compose** — verify everything runs with `docker compose up`

---

## 11. END-TO-END SUCCESS CRITERIA

The prototype is complete when ALL of these pass:

- [ ] Upload `discharge_complex.pdf` → extraction returns 4 diagnoses (J18.9, E11.9, I10, N18.3)
- [ ] FHIR bundle contains: Patient, Encounter, 4x Condition, MedicationRequest, Claim resources
- [ ] Reconciliation shows: 1 matched, 3 missed, ₹ delta > 0
- [ ] Web dashboard shows all 3 pages working, ₹ delta callout visible on reconcile page
- [ ] Android app can upload a PDF and show the reconciliation result
- [ ] FastAPI `/docs` shows all 8 endpoints with correct schemas
- [ ] FHIR service returns valid R4 Bundle JSON parseable by HAPI FHIR validator

---

## 12. KNOWN ISSUES TO HANDLE PROACTIVELY

- **Gemini rate limits**: Add exponential backoff retry (max 3 attempts, 2s/4s/8s) in `extractor.py`
- **Scanned PDFs**: If `pdfplumber` returns <100 chars, automatically fall back to Gemini Vision multimodal
- **CORS**: FastAPI CORS middleware is already included — web dashboard and Android must use `http://10.0.2.2:8000` (emulator) or `http://localhost:8000` (web)
- **FHIR service cold start**: Java Spring Boot takes ~15s to start — add health check polling in `docker-compose.yml`
- **ICD-10 code casing**: Normalize all codes to uppercase before comparison in reconciler
- **Demo offline**: Cache last successful extraction result in localStorage on the web dashboard in case of network issues during demo
- **HAPI FHIR version**: Use `7.0.0` — earlier versions have breaking API changes

---

## 13. DEMO PREPARATION CHECKLIST

Before the hackathon presentation:

1. Pre-run extraction on all 4 test PDFs and cache results in `EXTRACTIONS` dict (hardcode as fallback)
2. Test the full flow 3 times end-to-end without internet
3. Screenshot the reconcile page showing ₹14,200 delta — have it as a backup image
4. Have `discharge_complex.pdf` open in a separate tab ready to upload
5. Know your exact 8 sentences for each of the 5 demo moments (see pitch deck slide 9)

---

*NormClaim — Every diagnosis. Every rupee.*
*Built for Jilo Health Hackathon × NJACK IIT Patna — PS-2*
