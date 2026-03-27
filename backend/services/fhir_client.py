"""
NormClaim — FHIR Client Service
HTTP client for the Java HAPI FHIR microservice.
Sends extraction results to the FHIR service and receives FHIR R4 Bundle JSON.
"""

import os
import httpx
from models.schemas import ExtractionResult

FHIR_SERVICE_URL = os.environ.get(
    "FHIR_SERVICE_URL",
    "http://localhost:8001/fhir/bundle"
)


async def generate_fhir_bundle(extraction: ExtractionResult) -> dict:
    """
    Send extraction data to the Java FHIR service.
    Returns the FHIR R4 Bundle as a dict.
    """
    payload = extraction.model_dump()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(FHIR_SERVICE_URL, json=payload)
        resp.raise_for_status()
        return resp.json()


async def check_fhir_health() -> bool:
    """Check if the FHIR service is reachable."""
    health_url = FHIR_SERVICE_URL.replace("/fhir/bundle", "/fhir/health")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(health_url)
            return resp.status_code == 200
    except Exception:
        return False
