"""
Question + Section regeneration endpoints.

  POST /sessions/{session_id}/regenerate/question
  POST /sessions/{session_id}/regenerate/section

Both take the current PaperSchema + BlueprintSchema in the request body so the
server doesn't need to reload them from storage.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ai.regenerate import regenerate_question, regenerate_section
from ai.schemas import BlueprintSchema, PaperSchema, Question, SectionPaper

router = APIRouter(prefix="/sessions/{session_id}/regenerate", tags=["regenerate"])


class RegenerateQuestionRequest(BaseModel):
    paper: PaperSchema
    blueprint: BlueprintSchema
    question_id: str
    nudge: Optional[str] = None


class RegenerateSectionRequest(BaseModel):
    paper: PaperSchema
    blueprint: BlueprintSchema
    section_id: str
    nudge: Optional[str] = None


@router.post(
    "/question",
    response_model=Question,
    summary="Regenerate one question",
    description="Returns a new Question with the same id/marks/number as the original.",
)
def regenerate_one_question(
    session_id: UUID,
    payload: RegenerateQuestionRequest,
) -> Question:
    try:
        return regenerate_question(
            payload.paper,
            payload.blueprint,
            payload.question_id,
            payload.nudge,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {exc}")


@router.post(
    "/section",
    response_model=SectionPaper,
    summary="Regenerate an entire section",
    description=(
        "Returns a new SectionPaper with the same id/marks/question-count as "
        "the original, but every question content is regenerated."
    ),
)
def regenerate_one_section(
    session_id: UUID,
    payload: RegenerateSectionRequest,
) -> SectionPaper:
    try:
        return regenerate_section(
            payload.paper,
            payload.blueprint,
            payload.section_id,
            payload.nudge,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Section regeneration failed: {exc}")
