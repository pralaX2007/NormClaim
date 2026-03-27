"""
NormClaim — Validation Router
Runs validation and anomaly checks over extraction results.
"""

from fastapi import APIRouter, HTTPException

from services.validation_service import validate_extraction, detect_claim_anomalies
from routers.extract import EXTRACTIONS

router = APIRouter(prefix="/api/validate", tags=["Validation"])


@router.get("/{document_id}")
async def validate_document(document_id: str):
    """Validate extracted entities and detect claim anomalies."""
    extraction = EXTRACTIONS.get(document_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extract first: POST /api/extract/{id}")

    validation = validate_extraction(extraction)
    anomalies = detect_claim_anomalies(extraction)

    return {
        "document_id": document_id,
        "validation": validation,
        "anomalies": anomalies,
    }
