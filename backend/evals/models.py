"""SQLModel tables for eval runs and per-check results."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Column, Field, JSON, SQLModel


class EvalRun(SQLModel, table=True):
    __tablename__ = "eval_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    git_sha: str = ""
    suite: str = "deterministic"
    generation_model: str = ""
    judge_model: str = ""
    judge_prompt_version: str = ""
    offline: bool = False
    notes: str = ""


class EvalResult(SQLModel, table=True):
    __tablename__ = "eval_results"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="eval_runs.id", index=True)
    surface: str  # blueprint | generation | regenerate | answer_key | dedup | judge
    case_id: str  # which golden case, e.g. "blueprint_setA"
    metric: str   # e.g. "total_marks_drift_pct", "answer_coverage"
    value: float = 0.0
    passed: Optional[bool] = None  # None = informational metric, no pass/fail
    detail: dict = Field(default_factory=dict, sa_column=Column(JSON))
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
