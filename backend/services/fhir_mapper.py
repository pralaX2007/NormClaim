"""
NormClaim — Local FHIR Mapping Service
Builds a minimal FHIR R4 Bundle from extraction output when Java HAPI service
is not available.
"""

import uuid
from typing import Any, Dict, List

from models.schemas import ExtractionResult


def _resource_entry(resource: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "fullUrl": f"urn:uuid:{resource['id']}",
        "resource": resource,
    }


def _coding_block(system: str, code: str, display: str, text: str) -> Dict[str, Any]:
    return {
        "coding": [
            {
                "system": system,
                "code": code,
                "display": display,
            }
        ],
        "text": text,
    }


def build_fhir_bundle_local(extraction: ExtractionResult) -> Dict[str, Any]:
    """Map ExtractionResult to a basic FHIR R4 Bundle payload."""
    patient_id = str(uuid.uuid4())
    encounter_id = str(uuid.uuid4())

    patient: Dict[str, Any] = {
        "resourceType": "Patient",
        "id": patient_id,
        "name": [{"text": extraction.patient.name}] if extraction.patient.name else [],
    }
    if extraction.patient.sex:
        patient["gender"] = extraction.patient.sex.lower()
    if extraction.patient.abha_id:
        patient["identifier"] = [
            {
                "system": "https://abdm.gov.in/abha",
                "value": extraction.patient.abha_id,
            }
        ]

    encounter: Dict[str, Any] = {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "subject": {"reference": f"Patient/{patient_id}"},
    }
    if extraction.encounter.admit_date or extraction.encounter.discharge_date:
        encounter["period"] = {
            "start": extraction.encounter.admit_date,
            "end": extraction.encounter.discharge_date,
        }

    entries: List[Dict[str, Any]] = [_resource_entry(patient), _resource_entry(encounter)]

    claim_diagnoses: List[Dict[str, Any]] = []

    for index, diagnosis in enumerate(extraction.diagnoses, start=1):
        if diagnosis.negated:
            continue

        condition_id = str(uuid.uuid4())
        code = diagnosis.icd10_code
        display = diagnosis.icd10_display or diagnosis.text
        text = diagnosis.text

        condition = {
            "resourceType": "Condition",
            "id": condition_id,
            "subject": {"reference": f"Patient/{patient_id}"},
            "encounter": {"reference": f"Encounter/{encounter_id}"},
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}],
                "text": "confirmed",
            },
            "code": _coding_block(
                diagnosis.icd10_system,
                code,
                display,
                text,
            ),
        }
        entries.append(_resource_entry(condition))

        claim_diagnoses.append(
            {
                "sequence": index,
                "diagnosisCodeableConcept": _coding_block(
                    diagnosis.icd10_system,
                    code,
                    display,
                    text,
                ),
            }
        )

    for medication in extraction.medications:
        med_id = str(uuid.uuid4())
        med_display = medication.generic_name or medication.name or medication.brand_name or "Unknown Medication"
        med_text = medication.name or medication.brand_name or med_display

        med_request = {
            "resourceType": "MedicationRequest",
            "id": med_id,
            "status": "active",
            "intent": "order",
            "subject": {"reference": f"Patient/{patient_id}"},
            "encounter": {"reference": f"Encounter/{encounter_id}"},
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": medication.generic_name or med_display,
                        "display": med_display,
                    }
                ],
                "text": med_text,
            },
        }
        entries.append(_resource_entry(med_request))

    claim = {
        "resourceType": "Claim",
        "id": str(uuid.uuid4()),
        "status": "active",
        "type": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "institutional", "display": "Institutional"}],
            "text": "Institutional",
        },
        "use": "claim",
        "patient": {"reference": f"Patient/{patient_id}"},
        "diagnosis": claim_diagnoses,
    }
    entries.append(_resource_entry(claim))

    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "collection",
        "entry": entries,
    }
