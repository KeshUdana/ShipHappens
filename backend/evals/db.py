"""DB helpers for the eval framework. Reuses the app's engine (Supabase Postgres)."""

from sqlmodel import Session, SQLModel

from app.database import engine
from evals.models import EvalResult, EvalRun


def init_eval_tables() -> None:
    """Create eval tables if they don't exist (additive — no migration needed)."""
    SQLModel.metadata.create_all(
        engine, tables=[EvalRun.__table__, EvalResult.__table__]
    )


def eval_session() -> Session:
    return Session(engine)
