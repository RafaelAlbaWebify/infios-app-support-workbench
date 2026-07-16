from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, model_validator


def _new_id() -> str:
    return f"problem-{uuid4().hex[:12]}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProblemStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    KNOWN_ERROR = "known_error"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ProblemStatusChange(BaseModel):
    from_status: ProblemStatus
    to_status: ProblemStatus
    changed_by: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)
    changed_at: datetime = Field(default_factory=_utc_now)


class ProblemRecord(BaseModel):
    problem_id: str = Field(default_factory=_new_id)
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    status: ProblemStatus = ProblemStatus.OPEN
    owner: str = Field(min_length=1, max_length=200)
    created_by: str = Field(min_length=1, max_length=200)
    case_ids: list[str] = Field(min_length=1, max_length=200)
    recurrence_notes: str | None = Field(default=None, max_length=4000)
    status_history: list[ProblemStatusChange] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def prevent_duplicate_cases(self) -> ProblemRecord:
        if len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError("A support case cannot be linked to the same problem more than once.")
        return self

    @computed_field
    @property
    def occurrence_count(self) -> int:
        return len(self.case_ids)
