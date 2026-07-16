from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id() -> str:
    return f"handover-{uuid4().hex[:12]}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HandoverCaseItem(BaseModel):
    case_id: str = Field(min_length=1)
    status_summary: str = Field(min_length=1, max_length=2000)
    next_action: str = Field(min_length=1, max_length=2000)
    blocker: str | None = Field(default=None, max_length=2000)
    attention_required: bool = False


class ShiftHandover(BaseModel):
    handover_id: str = Field(default_factory=_new_id)
    shift_label: str = Field(min_length=1, max_length=200)
    prepared_by: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    cases: list[HandoverCaseItem] = Field(min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> ShiftHandover:
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("A shift handover cannot contain the same case more than once.")
        return self
