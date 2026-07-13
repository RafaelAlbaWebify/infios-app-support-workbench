from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseStatus(str, Enum):
    NEW = "new"
    INFORMATION_GATHERING = "information_gathering"
    INVESTIGATION = "investigation"
    WAITING_FOR_USER = "waiting_for_user"
    WAITING_FOR_ESCALATION = "waiting_for_escalation"
    ESCALATED = "escalated"
    WAITING_FOR_ANOTHER_TEAM = "waiting_for_another_team"
    BLOCKED = "blocked"
    RECOVERY_VALIDATION = "recovery_validation"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CertaintyLevel(str, Enum):
    TECHNICALLY_CONFIRMED = "technically_confirmed"
    REPRODUCED = "reproduced"
    REPORTED = "reported"
    SUSPECTED = "suspected"
    UNKNOWN = "unknown"


class EvidenceSensitivity(str, Enum):
    PUBLIC_SAMPLE = "public_sample"
    INTERNAL = "internal"
    PERSONAL_DATA = "personal_data"
    CREDENTIAL_OR_SECRET = "credential_or_secret"
    RESTRICTED = "restricted"


class ExplanationStatus(str, Enum):
    PROPOSED = "proposed"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    RULED_OUT = "ruled_out"
    CONFIRMED = "confirmed"


class ActionSafetyLevel(str, Enum):
    L1_SAFE = "l1_safe"
    APPROVED_RUNBOOK_REQUIRED = "approved_runbook_required"
    ESCALATION_REQUIRED = "escalation_required"


class ActionStatus(str, Enum):
    RECOMMENDED = "recommended"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class TimestampPrecision(str, Enum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class SupportCase(BaseModel):
    case_id: str = Field(default_factory=lambda: _new_id("case"))
    title: str = Field(min_length=1)
    application: str = Field(min_length=1)
    environment: str = "unknown"
    status: CaseStatus = CaseStatus.NEW
    severity: str = "unknown"
    impact: str = "unknown"
    owner: str | None = None
    affected_scope: str = "unknown"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=lambda: _new_id("evidence"))
    case_id: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    observed_at: datetime | None = None
    collected_at: datetime = Field(default_factory=_utc_now)
    content: str | dict[str, Any]
    certainty: CertaintyLevel = CertaintyLevel.UNKNOWN
    sensitivity: EvidenceSensitivity = EvidenceSensitivity.INTERNAL
    redacted: bool = False
    attachment_reference: str | None = None
    notes: str | None = None


class Observation(BaseModel):
    observation_id: str = Field(default_factory=lambda: _new_id("observation"))
    case_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    category: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    certainty: CertaintyLevel
    created_at: datetime = Field(default_factory=_utc_now)


class PossibleExplanation(BaseModel):
    explanation_id: str = Field(default_factory=lambda: _new_id("explanation"))
    case_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    status: ExplanationStatus = ExplanationStatus.PROPOSED
    supporting_observation_ids: list[str] = Field(default_factory=list)
    contradicting_observation_ids: list[str] = Field(default_factory=list)
    validation_action_ids: list[str] = Field(default_factory=list)
    confirmed_by_operator: bool = False

    @model_validator(mode="after")
    def require_evidence_for_confirmation(self) -> PossibleExplanation:
        if self.status is ExplanationStatus.CONFIRMED:
            if not self.confirmed_by_operator:
                raise ValueError("A confirmed explanation requires explicit operator confirmation.")
            if not self.supporting_observation_ids:
                raise ValueError("A confirmed explanation requires supporting observations.")
        return self


class DiagnosticAction(BaseModel):
    action_id: str = Field(default_factory=lambda: _new_id("action"))
    case_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    safety_level: ActionSafetyLevel
    status: ActionStatus = ActionStatus.RECOMMENDED
    requires_write_or_restart: bool = False
    expected_result: str | None = None
    actual_result: str | None = None
    conclusion: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    performed_by: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def enforce_action_safety_and_completion(self) -> DiagnosticAction:
        if self.requires_write_or_restart and self.safety_level is ActionSafetyLevel.L1_SAFE:
            raise ValueError("Write or restart actions cannot be classified as L1-safe.")
        if self.status is ActionStatus.COMPLETED and not self.actual_result:
            raise ValueError("A completed diagnostic action requires an actual result.")
        return self


class TimelineEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: _new_id("event"))
    case_id: str = Field(min_length=1)
    timestamp: datetime | None = None
    timestamp_precision: TimestampPrecision = TimestampPrecision.UNKNOWN
    event_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_reference: str = Field(min_length=1)
    certainty: CertaintyLevel = CertaintyLevel.UNKNOWN


class EscalationPackage(BaseModel):
    package_id: str = Field(default_factory=lambda: _new_id("escalation"))
    case_id: str = Field(min_length=1)
    target_team: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=_utc_now)
    included_evidence_ids: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    requested_action: str = Field(min_length=1)
    report_text: str = Field(min_length=1)
