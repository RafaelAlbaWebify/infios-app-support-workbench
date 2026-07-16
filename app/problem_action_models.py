from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id() -> str:
    return f"problem-action-{uuid4().hex[:12]}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProblemActionType(str, Enum):
    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"
    MONITORING = "monitoring"
    DOCUMENTATION = "documentation"


class ProblemActionStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    VALIDATED = "validated"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class ProblemActionSafety(str, Enum):
    READ_ONLY = "read_only"
    APPROVED_CHANGE_REQUIRED = "approved_change_required"
    ESCALATION_REQUIRED = "escalation_required"


class ProblemCorrectiveAction(BaseModel):
    action_id: str = Field(default_factory=_new_id)
    problem_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    action_type: ProblemActionType
    status: ProblemActionStatus = ProblemActionStatus.PLANNED
    safety: ProblemActionSafety
    owner: str = Field(min_length=1, max_length=200)
    created_by: str = Field(min_length=1, max_length=200)
    due_date: date | None = None
    requires_write_or_restart: bool = False
    implementation_evidence_reference: str | None = Field(default=None, max_length=500)
    validation_result: str | None = Field(default=None, max_length=4000)
    completed_by: str | None = Field(default=None, max_length=200)
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def enforce_safety_and_completion(self) -> ProblemCorrectiveAction:
        if self.requires_write_or_restart and self.safety is ProblemActionSafety.READ_ONLY:
            raise ValueError("Write or restart actions cannot be classified as read-only.")
        if self.status in {ProblemActionStatus.IMPLEMENTED, ProblemActionStatus.VALIDATED}:
            if not self.implementation_evidence_reference:
                raise ValueError("Implemented actions require an implementation evidence reference.")
            if not self.completed_by or self.completed_at is None:
                raise ValueError("Implemented actions require completion operator and timestamp.")
        if self.status is ProblemActionStatus.VALIDATED and not self.validation_result:
            raise ValueError("Validated actions require a validation result.")
        return self
