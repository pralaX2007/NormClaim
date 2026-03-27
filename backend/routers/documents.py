"""
NormClaim — Documents Router
Handles PDF upload and document listing.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import uuid
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# In-memory store (imported from main app state)
# These references are set by main.py at startup
DOCUMENTS: dict = {}

def _get_supabase_client():
    try:
        from main import supabase  # Local import avoids circular import at module load.
        return supabase
    except Exception:
        return None

@router.post("", response_model=dict)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document to Supabase Storage. Returns document_id."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    # Generate unique document ID
    doc_id = str(uuid.uuid4())
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    storage_path = f"documents/{doc_id}/{file.filename}"
    supabase = _get_supabase_client()

    # Keep in-memory bytes for extraction service.
    DOCUMENTS[doc_id] = {
        "filename": file.filename,
        "size": len(file_bytes),
        "bytes": file_bytes,
    }

    # Upload file to Supabase Storage (best-effort if configured)
    if supabase is not None:
        try:
            supabase.storage.from_("documents").upload(
                f"{doc_id}/{file.filename}", file_bytes
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Supabase Storage error: {str(e)}")

    # Insert metadata into Supabase database
    metadata = {
        "id": doc_id,
        "filename": file.filename,
        "storage_path": storage_path,
        "status": "uploaded",
        "consent_obtained": False,
    }
    if supabase is not None:
        try :
            supabase.table("documents").insert(metadata).execute()
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Supabase DB error: {str(e)}")

    return JSONResponse(content=jsonable_encoder(metadata))


@router.get("")
async def list_documents():
    """List all uploaded documents with their processing status."""
    from routers.extract import EXTRACTIONS
    from routers.reconcile import REPORTS
    supabase = _get_supabase_client()
    if supabase is not None:
        try:
            rows = supabase.table("documents").select("id,filename").execute().data or []
            return [
                {
                    "document_id": r["id"],
                    "filename": r["filename"],
                    "size_bytes": DOCUMENTS.get(r["id"], {}).get("size"),
                    "has_extraction": r["id"] in EXTRACTIONS,
                    "has_report": r["id"] in REPORTS,
                }
                for r in rows
            ]
        except Exception:
            pass

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
