"""
NormClaim — Pydantic Data Models
All I/O schemas for the NormClaim API.
"""

from pydantic import BaseModel
from typing import List, Optional


class PatientInfo(BaseModel):
    name: str
    age: Optional[int] = None
    sex: Optional[str] = None
    abha_id: Optional[str] = None


class EncounterInfo(BaseModel):
    admit_date: Optional[str] = None
    discharge_date: Optional[str] = None
    ward: Optional[str] = None
    los_days: Optional[int] = None


class Diagnosis(BaseModel):
    text: str
    icd10_code: str
    is_primary: bool
    confidence: float  # 0.0 – 1.0


class Procedure(BaseModel):
    text: str
    date: Optional[str] = None


class Medication(BaseModel):
    name: str
    dose: Optional[str] = None
    duration: Optional[str] = None


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
    estimated_value_inr: Optional[float] = None


class ReconciliationReport(BaseModel):
    document_id: str
    matched: List[ReconciliationItem]
    missed: List[ReconciliationItem]
    extra: List[ReconciliationItem]
    total_billed_codes: int
    total_extracted_codes: int
    estimated_claim_delta_inr: float
    confidence: float
