"""
Streaming paper generation endpoint — Feature #3.

POST /sessions/{session_id}/generate/stream
  Server-Sent Events (SSE) stream that emits progress events while Gemini
  generates the paper. The FE consumes with EventSource and updates a progress
  indicator in real time.
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.source_file import SourceFile
from ai.generate import generate_paper_stream
from ai.schemas import BlueprintSchema

router = APIRouter(prefix="/sessions/{session_id}/generate", tags=["streaming"])


class StreamRequest(BaseModel):
    blueprint: BlueprintSchema


def _sse_event(payload: dict) -> bytes:
    """Encode a dict as a Server-Sent Event frame."""
    data = json.dumps(payload, ensure_ascii=False)
    return f"data: {data}\n\n".encode("utf-8")


@router.post(
    "/stream",
    summary="Generate a paper with live progress (SSE)",
    description=(
        "Server-Sent Events endpoint. Yields events of shape "
        "{event: start|chunk|section|complete|error, ...}. "
        "The final event is 'complete' with the full PaperSchema in payload.paper."
    ),
)
def stream_paper(
    session_id: UUID,
    payload: StreamRequest,
    db: Session = Depends(get_session),
) -> StreamingResponse:
    files: list[SourceFile] = db.exec(
        select(SourceFile).where(SourceFile.session_id == session_id)
    ).all()
    file_uris = [f.gemini_file_uri for f in files if f.gemini_file_uri]

    if not file_uris:
        raise HTTPException(
            status_code=422,
            detail="No Gemini file URIs cached. Run blueprint extraction first.",
        )

    def event_source():
        for event in generate_paper_stream(payload.blueprint, file_uris):
            yield _sse_event(event)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx: don't buffer
        },
    )
