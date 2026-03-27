"""
NormClaim — Documents Router
Handles PDF upload and document listing.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import uuid
from supabase import Client
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# In-memory store (imported from main app state)
# These references are set by main.py at startup
DOCUMENTS: dict = {}

# Supabase client (imported from main app state)
from main import supabase

@router.post("", response_model=dict)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document to Supabase Storage. Returns document_id."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    # Generate unique document ID
    doc_id = str(uuid.uuid4())

    # Upload file to Supabase Storage
    try:
        storage_response = supabase.storage.from_("documents").upload(
            f"{doc_id}/{file.filename}", file.file
        )
        if not storage_response:
            raise HTTPException(status_code=500, detail="Failed to upload file to Supabase Storage")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase Storage error: {str(e)}")

    # Insert metadata into Supabase database
    try:
        metadata = {
            "id": doc_id,
            "filename": file.filename,
            "storage_path": f"documents/{doc_id}/{file.filename}",
            "uploaded_at": "now()",
            "status": "uploaded",
            "consent_obtained": False,
        }
        supabase.table("documents").insert(metadata).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase DB error: {str(e)}")

    return JSONResponse(content=jsonable_encoder(metadata))


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
