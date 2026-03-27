"""
NormClaim — Validation and Error Detection Service
Performs consistency and quality checks on extracted clinical data.
"""

from typing import Dict, List

from models.schemas import ExtractionResult


LOW_CONFIDENCE_THRESHOLD = 0.60


def validate_extraction(extraction: ExtractionResult) -> Dict[str, object]:
    """Run structural and clinical sanity checks for extraction output."""
    errors: List[str] = []
    warnings: List[str] = []

    if not extraction.diagnoses:
        errors.append("No diagnoses extracted")

    for idx, diagnosis in enumerate(extraction.diagnoses):
        if not diagnosis.icd10_code:
            errors.append(f"diagnoses[{idx}] missing icd10_code")
        if diagnosis.confidence < LOW_CONFIDENCE_THRESHOLD:
            warnings.append(
                f"diagnoses[{idx}] low confidence ({diagnosis.confidence:.2f})"
            )
        if diagnosis.negated and diagnosis.icd10_code in extraction.billed_codes:
            errors.append(
                f"diagnoses[{idx}] is negated but present in billed_codes"
            )

    for code in extraction.billed_codes:
        if code in extraction.negated_spans:
            warnings.append(
                f"billed code {code} appears related to negated span; review needed"
            )

    if extraction.detected_script not in (None, "roman", "devanagari", "mixed"):
        warnings.append("detected_script has unexpected value")

    return {
        "errors": errors,
        "warnings": warnings,
        "is_valid": len(errors) == 0,
    }


def detect_claim_anomalies(extraction: ExtractionResult) -> List[str]:
    """Return claim-level anomaly hints for downstream review UI."""
    anomalies: List[str] = []

    diagnosis_codes = {d.icd10_code for d in extraction.diagnoses if not d.negated}
    billed_codes = set(extraction.billed_codes)

    missed = diagnosis_codes - billed_codes
    if missed:
        anomalies.append(f"Potential undercoding: {len(missed)} diagnosis code(s) not billed")

    extra = billed_codes - diagnosis_codes
    if extra:
        anomalies.append(f"Potential overbilling: {len(extra)} billed code(s) not supported")

    low_conf = [d for d in extraction.diagnoses if d.confidence < LOW_CONFIDENCE_THRESHOLD]
    if low_conf:
        anomalies.append(f"{len(low_conf)} low-confidence diagnosis mapping(s) require review")

    return anomalies
