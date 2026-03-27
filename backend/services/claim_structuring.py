"""
NormClaim — Claim Structuring Engine
Structures extracted clinical data into a claim-ready format.
"""

from typing import Dict, Any

def structure_claim(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structure extracted clinical data into a claim-ready format.

    Args:
        data (Dict[str, Any]): Extracted clinical data.

    Returns:
        Dict[str, Any]: Structured claim data.
    """
    claim = {
        "patient": {
            "name": data.get("patient", {}).get("name"),
            "age": data.get("patient", {}).get("age"),
            "sex": data.get("patient", {}).get("sex"),
            "abha_id": data.get("patient", {}).get("abha_id"),
        },
        "encounter": {
            "admit_date": data.get("encounter", {}).get("admit_date"),
            "discharge_date": data.get("encounter", {}).get("discharge_date"),
            "ward": data.get("encounter", {}).get("ward"),
            "los_days": data.get("encounter", {}).get("los_days"),
        },
        "diagnoses": [
            {
                "text": d.get("text"),
                "icd10_code": d.get("icd10_code"),
                "is_primary": d.get("is_primary"),
                "confidence": d.get("confidence"),
            }
            for d in data.get("diagnoses", [])
        ],
        "procedures": [
            {
                "text": p.get("text"),
                "date": p.get("date"),
            }
            for p in data.get("procedures", [])
        ],
        "medications": [
            {
                "name": m.get("name"),
                "dose": m.get("dose"),
                "duration": m.get("duration"),
            }
            for m in data.get("medications", [])
        ],
        "billed_codes": data.get("billed_codes", []),
    }

    return claim