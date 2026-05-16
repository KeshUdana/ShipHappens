"""
Blueprint extraction endpoint — PBI-06.

POST /sessions/{session_id}/blueprint
  Finds all SourceFiles for the session, calls ai.blueprint.extract_blueprint(),
  and returns the PaperBlueprint JSON.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.source_file import SourceFile
from ai.blueprint import extract_blueprint
from ai.schemas import BlueprintSchema

router = APIRouter(prefix="/sessions/{session_id}/blueprint", tags=["blueprint"])


@router.post(
    "/",
    response_model=BlueprintSchema,
    summary="Extract a blueprint from uploaded source papers",
    description=(
        "Reads all SourceFile records for the session, uploads each PDF to "
        "the Gemini Files API, and returns a structured PaperBlueprint. "
        "Requires at least 1 uploaded PDF. Cached Gemini URIs are re-used "
        "when available."
    ),
)
def extract_session_blueprint(
    session_id: UUID,
    db: Session = Depends(get_session),
) -> BlueprintSchema:
    # Fetch all source files for this session
    files: list[SourceFile] = db.exec(
        select(SourceFile).where(SourceFile.session_id == session_id)
    ).all()

    if not files:
        raise HTTPException(
            status_code=422,
            detail="No uploaded files found for this session. Upload at least one PDF first.",
        )

    # Use cached Gemini URIs where available; fall back to local upload
    from pathlib import Path as _Path
    from ai.blueprint import _upload_pdf

    file_uris: list[str] = []
    for f in files:
        if f.gemini_file_uri:
            file_uris.append(f.gemini_file_uri)
        else:
            # FS2's storage adapter should populate gemini_file_uri on upload.
            # As a fallback, upload now from local disk.
            local_path = _Path(f.storage_path)
            if not local_path.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"File not found on disk and no Gemini URI cached: {f.filename}",
                )
            uri = _upload_pdf(local_path)
            # Cache the URI so subsequent calls don't re-upload
            f.gemini_file_uri = uri
            db.add(f)
            db.commit()
            file_uris.append(uri)

    try:
        blueprint = extract_blueprint(file_uris)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Blueprint extraction failed: {exc}",
        )

    return blueprint
