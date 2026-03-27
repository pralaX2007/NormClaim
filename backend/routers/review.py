"""
NormClaim — Human Review Router
Endpoints for reviewer notes and correction submission.
"""

from fastapi import APIRouter, HTTPException

from models.schemas import HumanReview
from services.review_service import save_review, get_review

router = APIRouter(prefix="/api/review", tags=["Human Review"])


def _get_supabase_client():
    try:
        from main import supabase
        return supabase
    except Exception:
        return None


@router.post("/{document_id}", response_model=HumanReview)
async def submit_review(document_id: str, review: HumanReview):
    """Store reviewer notes and structured corrections for a document."""
    if review.document_id != document_id:
        raise HTTPException(status_code=400, detail="Path document_id and payload document_id must match")

    saved = save_review(review, _get_supabase_client())
    return saved


@router.get("/{document_id}", response_model=HumanReview)
async def fetch_review(document_id: str):
    """Get the latest review for a document."""
    review = get_review(document_id, _get_supabase_client())
    if review is None:
        raise HTTPException(status_code=404, detail="No review found")
    return review
