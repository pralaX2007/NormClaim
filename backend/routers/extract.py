"""
NormClaim — Extract Router
Handles AI extraction of clinical entities from uploaded documents.
"""

from fastapi import APIRouter, HTTPException
from models.schemas import ExtractionResult
from services.extractor import extract_from_document
from routers.documents import DOCUMENTS
from nlp_pipe.extraction_pipeline import process_text

router = APIRouter(prefix="/api/extract", tags=["Extraction"])

# In-memory extraction results store
EXTRACTIONS: dict = {}


@router.post("/{document_id}", response_model=dict)
async def extract_document(document_id: str):
    """Run NLP extraction on an uploaded document."""
    if document_id not in DOCUMENTS:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get the raw text from the document bytes
    raw_text = DOCUMENTS[document_id]["bytes"].decode("utf-8", errors="ignore")

    # Process the text through the NLP pipeline
    try:
        extraction_result = process_text(raw_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NLP extraction error: {str(e)}")

    # Store the result in the in-memory EXTRACTIONS store
    EXTRACTIONS[document_id] = extraction_result

    return extraction_result


@router.get("/{document_id}", response_model=ExtractionResult)
async def get_extraction(document_id: str):
    """Retrieve a previous extraction result."""
    if document_id not in EXTRACTIONS:
        raise HTTPException(status_code=404, detail="Not extracted yet")
    return EXTRACTIONS[document_id]
