"""
NormClaim — Human Review Service
Persists reviewer corrections for extracted outputs.
"""

from typing import Dict, Optional

from models.schemas import HumanReview, CorrectionItem

# In-memory fallback cache for local dev when Supabase is not configured.
REVIEWS: Dict[str, HumanReview] = {}


def save_review(review: HumanReview, supabase_client: Optional[object] = None) -> HumanReview:
    """Persist a human review to Supabase (or in-memory fallback)."""
    REVIEWS[review.document_id] = review

    if supabase_client is not None:
        supabase_client.table("human_reviews").insert(
            {
                "document_id": review.document_id,
                "reviewer_notes": review.reviewer_notes,
                "corrections_json": [c.model_dump() for c in review.corrections],
                "reviewed_at": review.reviewed_at,
            }
        ).execute()

    return review


def get_review(document_id: str, supabase_client: Optional[object] = None) -> Optional[HumanReview]:
    """Fetch latest human review for a document."""
    if supabase_client is not None:
        resp = (
            supabase_client.table("human_reviews")
            .select("document_id, reviewer_notes, corrections_json, reviewed_at")
            .eq("document_id", document_id)
            .order("reviewed_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            row = rows[0]
            corrections = [CorrectionItem(**c) for c in (row.get("corrections_json") or [])]
            return HumanReview(
                document_id=row["document_id"],
                reviewer_notes=row.get("reviewer_notes", ""),
                corrections=corrections,
                reviewed_at=row.get("reviewed_at", ""),
            )

    return REVIEWS.get(document_id)
