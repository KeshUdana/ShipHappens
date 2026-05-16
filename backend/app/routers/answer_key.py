"""
Answer key generation endpoint — Feature #1.

POST /sessions/{session_id}/answer-key
  Accepts a PaperSchema (the current edited paper) and returns an AnswerKeySchema.

The teacher's edited paper is what gets answered — not the original generated paper.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.database import get_session
from ai.answer_key import generate_answer_key
from ai.schemas import AnswerKeySchema, PaperSchema

router = APIRouter(prefix="/sessions/{session_id}/answer-key", tags=["answer-key"])


@router.post(
    "/",
    response_model=AnswerKeySchema,
    summary="Generate an answer key + marking scheme",
    description=(
        "Takes the current PaperSchema in the request body and produces a "
        "1:1 mapped AnswerKeySchema containing model answers, marking criteria, "
        "and common mistakes for every question. Uses gemini-2.5-flash."
    ),
)
def create_answer_key(
    session_id: UUID,
    paper: PaperSchema,
    db: Session = Depends(get_session),
) -> AnswerKeySchema:
    try:
        return generate_answer_key(paper)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Answer key generation failed: {exc}",
        )
