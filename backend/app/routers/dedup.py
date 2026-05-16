"""
Duplicate-check endpoint — Feature #2.

POST /sessions/{session_id}/dedup
  Compares every generated question against the session's source PDFs and
  returns a list of DuplicateWarning entries.
"""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.source_file import SourceFile
from ai.dedup import check_duplicates
from ai.schemas import DuplicateWarning, PaperSchema

router = APIRouter(prefix="/sessions/{session_id}/dedup", tags=["dedup"])


class DedupRequest(BaseModel):
    paper: PaperSchema
    threshold: float = 0.80  # 0.80=medium, 0.90=high


class DedupResponse(BaseModel):
    warnings: list[DuplicateWarning]
    threshold: float
    n_source_files: int


@router.post(
    "/",
    response_model=DedupResponse,
    summary="Check for source-paper overlap",
    description=(
        "Embeds every question's text and compares against text from the session's "
        "source PDFs. Returns warnings for any question that is >= threshold similar "
        "to a source passage. Default threshold 0.80 (medium); 0.90+ is 'high' severity."
    ),
)
def check_paper_duplicates(
    session_id: UUID,
    payload: DedupRequest,
    db: Session = Depends(get_session),
) -> DedupResponse:
    files: list[SourceFile] = db.exec(
        select(SourceFile).where(SourceFile.session_id == session_id)
    ).all()
    if not files:
        raise HTTPException(
            status_code=422,
            detail="No source files for this session — nothing to compare against.",
        )

    pdf_paths = [Path(f.storage_path) for f in files if Path(f.storage_path).exists()]
    if not pdf_paths:
        raise HTTPException(
            status_code=500,
            detail="Source files missing from local storage.",
        )

    try:
        warnings = check_duplicates(payload.paper, pdf_paths, threshold=payload.threshold)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dedup check failed: {exc}")

    return DedupResponse(
        warnings=warnings,
        threshold=payload.threshold,
        n_source_files=len(pdf_paths),
    )
