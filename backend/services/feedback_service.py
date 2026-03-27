"""
NormClaim — Feedback Service
Stores extraction quality feedback for model/prompt improvement loops.
"""

from typing import Dict, List, Optional

from models.schemas import FeedbackItem

# In-memory fallback cache for local development.
FEEDBACK: Dict[str, List[FeedbackItem]] = {}


def save_feedback(item: FeedbackItem, supabase_client: Optional[object] = None) -> FeedbackItem:
    """Persist a feedback event to Supabase (or in-memory fallback)."""
    FEEDBACK.setdefault(item.document_id, []).append(item)

    if supabase_client is not None:
        supabase_client.table("feedback").insert(
            {
                "document_id": item.document_id,
                "was_correct": item.was_extraction_correct,
                "correction_type": item.correction_type,
                "details": item.details,
            }
        ).execute()

    return item


def get_feedback(document_id: str, supabase_client: Optional[object] = None) -> List[FeedbackItem]:
    """Fetch feedback history for a document."""
    if supabase_client is not None:
        resp = (
            supabase_client.table("feedback")
            .select("document_id, was_correct, correction_type, details")
            .eq("document_id", document_id)
            .execute()
        )
        rows = resp.data or []
        return [
            FeedbackItem(
                document_id=row["document_id"],
                was_extraction_correct=bool(row.get("was_correct")),
                correction_type=row.get("correction_type", ""),
                details=row.get("details", ""),
            )
            for row in rows
        ]

    return FEEDBACK.get(document_id, [])
