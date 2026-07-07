from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str = Field(..., description="Evidence source, such as user report, app log, API response, monitoring, or service desk note.")
    timestamp: str | None = Field(default=None, description="Timestamp if available.")
    detail: str = Field(..., description="Evidence detail.")
    confidence: Literal["low", "medium", "high"] = "medium"


class IncidentInput(BaseModel):
    incident_id: str
    title: str
    reported_by: str | None = None
    affected_users: list[str] = Field(default_factory=list)
    affected_service: str
    environment: Literal["sample", "dev", "test", "staging", "production-like"] = "sample"
    symptom: str
    user_impact: str
    http_status: int | None = None
    endpoint: str | None = None
    correlation_id: str | None = None
    recent_changes: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    operator_notes: str | None = None


class Finding(BaseModel):
    category: str
    severity: Literal["info", "low", "medium", "high"]
    statement: str
    evidence_refs: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    incident_id: str
    summary: str
    user_impact: str
    likely_causes: list[str]
    unknowns: list[str]
    missing_evidence: list[str]
    safe_next_steps: list[str]
    escalation_note: str
    rca_draft: str
    findings: list[Finding]
