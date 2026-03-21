"""
NormClaim — Documents Router
Handles PDF upload and document listing.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import uuid

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# In-memory store (imported from main app state)
# These references are set by main.py at startup
DOCUMENTS: dict = {}


@router.post("", response_model=dict)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document. Returns document_id."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    doc_id = str(uuid.uuid4())
    file_bytes = await file.read()
    DOCUMENTS[doc_id] = {
        "bytes": file_bytes,
        "filename": file.filename,
        "size": len(file_bytes),
    }
    return {
        "document_id": doc_id,
        "filename": file.filename,
        "status": "uploaded",
        "size_bytes": len(file_bytes),
    }


@router.get("")
async def list_documents():
    """List all uploaded documents with their processing status."""
    from routers.extract import EXTRACTIONS
    from routers.reconcile import REPORTS
    return [
        {
            "document_id": k,
            "filename": v["filename"],
            "size_bytes": v["size"],
            "has_extraction": k in EXTRACTIONS,
            "has_report": k in REPORTS,
        }
        for k, v in DOCUMENTS.items()
    ]
