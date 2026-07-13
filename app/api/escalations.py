from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.actions import get_action_repository
from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.explanations import get_explanation_repository
from app.api.observations import get_observation_repository
from app.domain.models import CertaintyLevel, EscalationPackage, ExplanationStatus
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_escalation_repository import SQLiteEscalationRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_explanation_repository import SQLiteExplanationRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository


router = APIRouter(prefix="/api/cases/{case_id}/escalations", tags=["escalations"])


class CreateEscalationRequest(BaseModel):
    target_team: str = Field(min_length=1)
    requested_action: str = Field(min_length=1)


class EscalationListResponse(BaseModel):
    escalations: list[EscalationPackage]
    count: int


@lru_cache(maxsize=1)
def get_escalation_repository() -> SQLiteEscalationRepository:
    return SQLiteEscalationRepository(DEFAULT_CASE_DATABASE)


def _render_report(
    support_case,
    evidence,
    observations,
    explanations,
    actions,
    requested_action: str,
    target_team: str,
) -> tuple[str, list[str]]:
    missing: list[str] = []
    if support_case.impact == "unknown":
        missing.append("Business impact is unknown.")
    if support_case.affected_scope == "unknown":
        missing.append("Affected scope is unknown.")
    if not evidence:
        missing.append("No evidence has been captured.")
    if not observations:
        missing.append("No evidence-backed observations have been recorded.")
    if not any(action.actual_result for action in actions):
        missing.append("No completed diagnostic action result is available.")

    confirmed = [
        observation
        for observation in observations
        if observation.certainty in {
            CertaintyLevel.TECHNICALLY_CONFIRMED,
            CertaintyLevel.REPRODUCED,
        }
    ]
    reported = [item for item in evidence if item.certainty is CertaintyLevel.REPORTED]
    possible = [
        item for item in explanations if item.status is not ExplanationStatus.CONFIRMED
    ]
    confirmed_explanations = [
        item for item in explanations if item.status is ExplanationStatus.CONFIRMED
    ]

    lines = [
        f"# Escalation: {support_case.title}",
        "",
        f"- Case ID: `{support_case.case_id}`",
        f"- Application: {support_case.application}",
        f"- Environment: {support_case.environment}",
        f"- Current status: {support_case.status.value}",
        f"- Severity: {support_case.severity}",
        f"- Target team: {target_team}",
        "",
        "## Business impact",
        "",
        support_case.impact,
        "",
        f"Affected scope: {support_case.affected_scope}",
        "",
        "## Confirmed observations",
        "",
    ]
    lines.extend(
        [f"- {item.statement} (`{item.observation_id}`)" for item in confirmed]
        or ["- None recorded."]
    )
    lines.extend(["", "## Reported but not technically confirmed", ""])
    lines.extend(
        [f"- {item.content} (`{item.evidence_id}`)" for item in reported]
        or ["- None recorded."]
    )
    lines.extend(["", "## Diagnostic actions and results", ""])
    lines.extend(
        [
            f"- {item.name}: {item.actual_result or 'No result recorded.'}"
            for item in actions
        ]
        or ["- None recorded."]
    )
    lines.extend(["", "## Possible explanations — unconfirmed", ""])
    lines.extend(
        [f"- {item.statement} [{item.status.value}]" for item in possible]
        or ["- None recorded."]
    )
    lines.extend(["", "## Confirmed explanations", ""])
    lines.extend(
        [f"- {item.statement}" for item in confirmed_explanations]
        or ["- None recorded."]
    )
    lines.extend(["", "## Missing information", ""])
    lines.extend([f"- {item}" for item in missing] or ["- No standard gaps detected."])
    lines.extend(
        [
            "",
            "## Requested support",
            "",
            requested_action,
            "",
            "## Safety statement",
            "",
            "This package distinguishes confirmed observations, reported information, and unconfirmed explanations. It does not treat temporal correlation or keyword matches as proof of root cause.",
        ]
    )
    return "\n".join(lines), missing


@router.post("", response_model=EscalationPackage, status_code=status.HTTP_201_CREATED)
def create_escalation(
    case_id: str,
    request: CreateEscalationRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
    explanation_repository: SQLiteExplanationRepository = Depends(get_explanation_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
    escalation_repository: SQLiteEscalationRepository = Depends(get_escalation_repository),
) -> EscalationPackage:
    support_case = case_repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")

    evidence = evidence_repository.list_for_case(case_id, limit=500)
    observations = observation_repository.list_for_case(case_id, limit=500)
    explanations = explanation_repository.list_for_case(case_id, limit=500)
    actions = action_repository.list_for_case(case_id, limit=500)
    report_text, missing = _render_report(
        support_case,
        evidence,
        observations,
        explanations,
        actions,
        request.requested_action,
        request.target_team,
    )
    package = EscalationPackage(
        case_id=case_id,
        target_team=request.target_team,
        included_evidence_ids=[item.evidence_id for item in evidence],
        missing_information=missing,
        requested_action=request.requested_action,
        report_text=report_text,
    )
    return escalation_repository.save(package)


@router.get("", response_model=EscalationListResponse)
def list_escalations(
    case_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    escalation_repository: SQLiteEscalationRepository = Depends(get_escalation_repository),
) -> EscalationListResponse:
    if case_repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    escalations = escalation_repository.list_for_case(case_id, limit=limit)
    return EscalationListResponse(escalations=escalations, count=len(escalations))


@router.get("/{package_id}", response_model=EscalationPackage)
def get_escalation(
    case_id: str,
    package_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    escalation_repository: SQLiteEscalationRepository = Depends(get_escalation_repository),
) -> EscalationPackage:
    if case_repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    package = escalation_repository.get(package_id)
    if package is None or package.case_id != case_id:
        raise HTTPException(status_code=404, detail="Escalation package not found")
    return package
