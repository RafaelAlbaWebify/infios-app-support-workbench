from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class RecoveryOutcome(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    UNABLE_TO_VALIDATE = "unable_to_validate"


class RecoveryValidation(BaseModel):
    validation_id: str = Field(default_factory=lambda: f"recovery-{uuid4().hex[:12]}")
    case_id: str = Field(min_length=1)
    outcome: RecoveryOutcome
    method: str = Field(min_length=1)
    result: str = Field(min_length=1)
    performed_by: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    tested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str | None = None

    @model_validator(mode="after")
    def passed_validation_requires_evidence(self) -> RecoveryValidation:
        if self.outcome is RecoveryOutcome.PASSED and not self.evidence_ids:
            raise ValueError("A passed recovery validation requires supporting evidence.")
        return self
