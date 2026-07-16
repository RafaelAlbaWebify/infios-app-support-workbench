from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id() -> str:
    return f"known-error-{uuid4().hex[:12]}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnownErrorStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


class WorkaroundSafety(str, Enum):
    READ_ONLY = "read_only"
    APPROVED_CHANGE_REQUIRED = "approved_change_required"
    ESCALATION_REQUIRED = "escalation_required"


class KnownErrorRecord(BaseModel):
    known_error_id: str = Field(default_factory=_new_id)
    problem_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    symptom_summary: str = Field(min_length=1, max_length=4000)
    workaround_steps: list[str] = Field(min_length=1, max_length=100)
    workaround_limitations: str = Field(min_length=1, max_length=4000)
    validation_guidance: str = Field(min_length=1, max_length=4000)
    safety: WorkaroundSafety
    requires_write_or_restart: bool = False
    status: KnownErrorStatus = KnownErrorStatus.DRAFT
    owner: str = Field(min_length=1, max_length=200)
    created_by: str = Field(min_length=1, max_length=200)
    approved_by: str | None = Field(default=None, max_length=200)
    approval_reason: str | None = Field(default=None, max_length=2000)
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def enforce_safety_and_publication(self) -> KnownErrorRecord:
        if self.requires_write_or_restart and self.safety is WorkaroundSafety.READ_ONLY:
            raise ValueError("Write or restart workarounds cannot be classified as read-only.")
        if self.status is KnownErrorStatus.PUBLISHED:
            if not self.approved_by or not self.approval_reason or self.approved_at is None:
                raise ValueError("Published known errors require approving operator, reason, and timestamp.")
        return self
