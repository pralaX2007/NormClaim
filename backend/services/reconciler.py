"""
NormClaim — Reconciliation Engine
Compares AI-extracted diagnoses against billed ICD-10 codes.
Surfaces missed diagnoses and estimates the claim gap in ₹.
"""

import os
import json
from models.schemas import ExtractionResult, ReconciliationReport, ReconciliationItem

# ── Load ICD-10 lookup ────────────────────────────────────────────────────
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
with open(os.path.join(_DATA_DIR, "icd10_codes.json")) as f:
    ICD10_LOOKUP: dict = json.load(f)

# ── Approximate claim value per ICD-10 code category (INR) ────────────────
# Based on AB-PMJAY package rate approximations — demo values
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
    """
    Core reconciliation logic:
    - Compare extracted diagnosis codes against billed codes
    - Identify matched, missed, and extra codes
    - Estimate ₹ claim delta for missed diagnoses
    """
    extracted_codes = {
        d.icd10_code.upper()
        for d in extraction.diagnoses
        if not d.negated
    }
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
