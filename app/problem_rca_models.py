from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id() -> str:
    return f"rca-{uuid4().hex[:12]}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RCAStatus(str, Enum):
    DRAFT = "draft"
    SUPPORTED = "supported"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ProblemRCAStatement(BaseModel):
    rca_id: str = Field(default_factory=_new_id)
    problem_id: str = Field(min_length=1)
    statement: str = Field(min_length=1, max_length=4000)
    status: RCAStatus = RCAStatus.DRAFT
    supporting_explanation_ids: list[str] = Field(default_factory=list, max_length=200)
    contradicting_explanation_ids: list[str] = Field(default_factory=list, max_length=200)
    created_by: str = Field(min_length=1, max_length=200)
    confirmed_by: str | None = Field(default=None, max_length=200)
    confirmation_reason: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    confirmed_at: datetime | None = None

    @model_validator(mode="after")
    def enforce_confirmation_requirements(self) -> ProblemRCAStatement:
        if set(self.supporting_explanation_ids) & set(self.contradicting_explanation_ids):
            raise ValueError("An explanation cannot both support and contradict the same RCA statement.")
        if self.status is RCAStatus.CONFIRMED:
            if not self.supporting_explanation_ids:
                raise ValueError("A confirmed RCA statement requires supporting explanations.")
            if not self.confirmed_by or not self.confirmation_reason or self.confirmed_at is None:
                raise ValueError("A confirmed RCA statement requires operator identity, reason, and timestamp.")
        return self
