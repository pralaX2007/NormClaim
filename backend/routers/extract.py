"""
NormClaim — Extract Router
Handles AI extraction of clinical entities from uploaded documents.
"""

from fastapi import APIRouter, HTTPException
from models.schemas import ExtractionResult
from services.extractor import extract_from_document
from routers.documents import DOCUMENTS

router = APIRouter(prefix="/api/extract", tags=["Extraction"])

# In-memory extraction results store
EXTRACTIONS: dict = {}


@router.post("/{document_id}", response_model=ExtractionResult)
async def extract_document(document_id: str):
    """Run AI extraction on an uploaded document."""
    if document_id not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found")
    result = extract_from_document(DOCUMENTS[document_id]["bytes"], document_id)
    EXTRACTIONS[document_id] = result
    return result


@router.get("/{document_id}", response_model=ExtractionResult)
async def get_extraction(document_id: str):
    """Retrieve a previous extraction result."""
    if document_id not in EXTRACTIONS:
        raise HTTPException(status_code=404, detail="Not extracted yet")
    return EXTRACTIONS[document_id]
