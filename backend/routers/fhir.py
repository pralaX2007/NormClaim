"""
NormClaim — FHIR Router
Proxies extraction data to the Java HAPI FHIR service to generate FHIR R4 Bundles.
"""

from fastapi import APIRouter, HTTPException
from services.fhir_client import generate_fhir_bundle, check_fhir_health
from routers.extract import EXTRACTIONS

router = APIRouter(prefix="/api/fhir", tags=["FHIR"])

# In-memory FHIR bundle cache
FHIR_BUNDLES: dict = {}


@router.post("/{document_id}")
async def create_fhir_bundle(document_id: str):
    """Generate a FHIR R4 Bundle from extraction results."""
    if document_id not in EXTRACTIONS:
        raise HTTPException(
            status_code=404,
            detail="Extract first: POST /api/extract/{id}"
        )

    # Check if FHIR service is up
    fhir_healthy = await check_fhir_health()
    if not fhir_healthy:
        raise HTTPException(
            status_code=503,
            detail="FHIR service is not available. Start fhir-service on port 8001."
        )

    bundle = await generate_fhir_bundle(EXTRACTIONS[document_id])
    FHIR_BUNDLES[document_id] = bundle
    return bundle


@router.get("/{document_id}")
async def get_fhir_bundle(document_id: str):
    """Retrieve a previously generated FHIR bundle."""
    if document_id not in FHIR_BUNDLES:
        raise HTTPException(status_code=404, detail="No FHIR bundle found")
    return FHIR_BUNDLES[document_id]
