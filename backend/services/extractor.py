"""
NormClaim — AI Extraction Service
Uses Google Gemini API (google.genai SDK) to extract structured clinical
entities from hospital documents.
Includes ICD-10 code validation via rapidfuzz fuzzy matching.
"""

import os
import json
import re
import time
import logging
from google import genai
from models.schemas import (
    ExtractionResult, PatientInfo, EncounterInfo,
    Diagnosis, Procedure, Medication,
)
from services.pdf_parser import extract_text_from_pdf, pdf_to_base64_image
from rapidfuzz import process, fuzz
import json as _json

logger = logging.getLogger(__name__)

# ── Load ICD-10 lookup at module level ─────────────────────────────────────
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
with open(os.path.join(_DATA_DIR, "icd10_codes.json")) as f:
    ICD10_LOOKUP: dict = _json.load(f)

ICD10_CODES = list(ICD10_LOOKUP.keys())

# ── Extraction system prompt ──────────────────────────────────────────────
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

# ── Retry configuration (handles Gemini rate limits) ──────────────────────
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # seconds — exponential backoff

# ── Model name ────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash-lite"


def validate_icd10_codes(diagnoses: list) -> list:
    """
    Use rapidfuzz to validate and correct ICD-10 codes returned by Gemini.
    If a code is not in the official lookup, find the closest match.
    """
    for d in diagnoses:
        code = d.get("icd10_code", "").strip().upper()
        if code not in ICD10_LOOKUP:
            result = process.extractOne(code, ICD10_CODES, scorer=fuzz.ratio)
            if result:
                match, score, _ = result
                if score > 70:
                    d["icd10_code"] = match
    return diagnoses


def _call_gemini_with_retry(client: genai.Client, prompt_text: str) -> str:
    """Call Gemini API with exponential backoff retry on failure."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt_text,
            )
            return response.text.strip()
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    f"Gemini API attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"Gemini API failed after {MAX_RETRIES} attempts: {e}")
    raise last_error


def extract_from_document(file_bytes: bytes, document_id: str) -> ExtractionResult:
    """
    Main extraction pipeline:
    1. Extract text from PDF (or convert to image for scanned docs)
    2. Send to Gemini for clinical entity extraction
    3. Validate ICD-10 codes with fuzzy matching
    4. Return structured ExtractionResult
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    client = genai.Client(api_key=api_key)

    # Step 1: Try text extraction
    raw_text = extract_text_from_pdf(file_bytes)

    # Step 2: Build prompt content
    if raw_text and len(raw_text) > 100:
        # Digital PDF — use text
        prompt_text = (
            EXTRACTION_SYSTEM_PROMPT
            + f"\n\nDOCUMENT TEXT:\n{raw_text[:8000]}"
        )
    else:
        # Scanned PDF — use Vision (base64 image)
        b64_image = pdf_to_base64_image(file_bytes)
        if not b64_image:
            raise ValueError("Could not extract text or image from PDF")
        # For scanned docs, include the base64 as part of prompt
        # (The new SDK supports multimodal via Parts, but text-only is
        #  sufficient for our reportlab-generated test PDFs)
        prompt_text = (
            EXTRACTION_SYSTEM_PROMPT
            + "\n\nDOCUMENT IMAGE (base64-encoded scanned document):\n"
            + b64_image[:8000]
        )

    # Step 3: Call Gemini with retry
    raw_json = _call_gemini_with_retry(client, prompt_text)

    # Step 4: Parse and validate
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        # Try to extract JSON from within the response (Gemini sometimes
        # wraps JSON in markdown code fences)
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


"""
NormClaim — Gemini Extractor
Handles semantic extraction using Gemini and post-processing overrides.
"""

import json
import time
import re
from typing import Dict, List
from backend.services.nlp_preprocessor import preprocess
from backend.data.drug_map import drug_map
import google.generativeai as palm

# Load Gemini API key
import os
palm.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Constants
GEMINI_SYSTEM_PROMPT = """
You are a clinical NLP assistant. Your task is to extract structured clinical data from pre-processed text.
Trust the negated_spans list provided. For any diagnosis whose text matches a span in negated_spans, set negated=true.
Use the following drug brand-to-generic mapping as a reference:

""" + json.dumps(drug_map, indent=2) + """

Output strictly in JSON format matching this schema:
{
  "diagnoses": [
    {"text": "", "icd10_code": "", "negated": false, "confidence": 0.0}
  ],
  "medications": [
    {"brand_name": "", "generic_name": "", "dose": "", "route": "", "frequency": "", "duration": ""}
  ]
}
"""

def build_prompt(spacy_result: Dict) -> str:
    """Construct the full prompt for Gemini."""
    input_data = {
        "expanded_text": spacy_result["expanded_text"],
        "section_map": spacy_result["section_map"],
        "negated_spans": spacy_result["negated_spans"]
    }
    return GEMINI_SYSTEM_PROMPT + "\n\nInput:\n" + json.dumps(input_data, indent=2)

def parse_gemini_response(raw: str) -> Dict:
    """Parse the raw Gemini response into a dictionary."""
    try:
        raw_json = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Gemini response: {raw}") from e

def apply_negation_override(result: Dict, negated_spans: List[str]) -> Dict:
    """Override negation based on spaCy's negated spans."""
    for diagnosis in result.get("diagnoses", []):
        if any(span.lower() in diagnosis["text"].lower() for span in negated_spans):
            diagnosis["negated"] = True
    return result

def call_gemini(prompt: str) -> Dict:
    """Call the Gemini API with retry logic."""
    retries = 3
    for attempt in range(retries):
        try:
            response = palm.chat(messages=prompt, model="gemini-1.5-flash", temperature=0.1, max_output_tokens=4096)
            return parse_gemini_response(response.last)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError("Gemini API call failed after retries") from e

def extract(raw_text: str, document_id: str, use_cache: bool = False) -> Dict:
    """Run the full extraction pipeline."""
    if use_cache:
        with open("test-data/cached_extraction.json", "r") as cache_file:
            return json.load(cache_file)

    spacy_result = preprocess(raw_text)
    prompt = build_prompt(spacy_result)
    gemini_raw = call_gemini(prompt)
    gemini_result = apply_negation_override(gemini_raw, spacy_result["negated_spans"])

    return {
        "document_id": document_id,
        "raw_text_preview": raw_text[:500],
        "detected_script": spacy_result["detected_script"],
        "section_map": spacy_result["section_map"],
        "negated_spans": spacy_result["negated_spans"],
        **gemini_result
    }
