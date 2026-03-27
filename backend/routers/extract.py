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
    """Run NLP extraction on an uploaded document."""
    if document_id not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found")

    file_bytes = DOCUMENTS[document_id].get("bytes")
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Document bytes missing")

    try:
        extraction_result = extract_from_document(file_bytes, document_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction error: {str(e)}")

    EXTRACTIONS[document_id] = extraction_result
    return extraction_result


@router.get("/{document_id}", response_model=ExtractionResult)
async def get_extraction(document_id: str):
    """Retrieve a previous extraction result."""
    if document_id not in EXTRACTIONS:
        raise HTTPException(status_code=404, detail="Not extracted yet")
    return EXTRACTIONS[document_id]
