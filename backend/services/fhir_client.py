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


"""
NormClaim — FHIR Mapping Layer
Maps extracted clinical data to FHIR resources.
"""

from typing import Dict, Any
from fhir.resources.patient import Patient
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.encounter import Encounter
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.fhirdate import FHIRDate
import uuid

def map_to_fhir_patient(data: Dict[str, Any]) -> Patient:
    """Map patient information to a FHIR Patient resource."""
    return Patient(
        id=str(uuid.uuid4()),
        name=[{
            "text": data.get("name")
        }] if data.get("name") else None,
        gender=data.get("sex"),
        birthDate=FHIRDate(data.get("birth_date")) if data.get("birth_date") else None,
        identifier=[{
            "system": "https://abha.gov.in",
            "value": data.get("abha_id")
        }] if data.get("abha_id") else None
    )

def map_to_fhir_encounter(data: Dict[str, Any]) -> Encounter:
    """Map encounter information to a FHIR Encounter resource."""
    return Encounter(
        id=str(uuid.uuid4()),
        period={
            "start": FHIRDate(data.get("admit_date")) if data.get("admit_date") else None,
            "end": FHIRDate(data.get("discharge_date")) if data.get("discharge_date") else None
        },
        class_fhir={"code": data.get("ward")} if data.get("ward") else None
    )

def map_to_fhir_condition(data: Dict[str, Any]) -> Condition:
    """Map diagnosis information to a FHIR Condition resource."""
    return Condition(
        id=str(uuid.uuid4()),
        code={"coding": [{
            "system": "http://hl7.org/fhir/sid/icd-10",
            "code": data.get("icd10_code"),
            "display": data.get("text")
        }]},
        clinicalStatus={"coding": [{"code": "active"}]},
        verificationStatus={"coding": [{"code": "confirmed"}]},
        subject={"reference": f"Patient/{data.get('patient_id')}"},
        onsetDateTime=FHIRDate(data.get("onset_date")) if data.get("onset_date") else None
    )

def map_to_fhir_medication(data: Dict[str, Any]) -> MedicationStatement:
    """Map medication information to a FHIR MedicationStatement resource."""
    return MedicationStatement(
        id=str(uuid.uuid4()),
        medicationCodeableConcept={"coding": [{
            "system": "http://hl7.org/fhir/sid/ndc",
            "code": data.get("generic_name"),
            "display": data.get("brand_name")
        }]},
        dosage=[{
            "text": f"{data.get('dose')} {data.get('route')} {data.get('frequency')} {data.get('duration')}"
        }],
        subject={"reference": f"Patient/{data.get('patient_id')}"}
    )

def build_fhir_bundle(extraction_result: Dict[str, Any]) -> Bundle:
    """Build a FHIR Bundle from the extraction result."""
    patient = map_to_fhir_patient(extraction_result.get("patient", {}))
    encounter = map_to_fhir_encounter(extraction_result.get("encounter", {}))

    conditions = [
        map_to_fhir_condition({**d, "patient_id": patient.id})
        for d in extraction_result.get("diagnoses", [])
    ]

    medications = [
        map_to_fhir_medication({**m, "patient_id": patient.id})
        for m in extraction_result.get("medications", [])
    ]

    entries = [
        BundleEntry(resource=patient),
        BundleEntry(resource=encounter),
        *[BundleEntry(resource=c) for c in conditions],
        *[BundleEntry(resource=m) for m in medications]
    ]

    return Bundle(
        id=str(uuid.uuid4()),
        type="collection",
        entry=entries
    )
