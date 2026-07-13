from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.api.escalations import get_escalation_repository
from app.api.evidence import get_evidence_repository
from app.api.explanations import get_explanation_repository
from app.api.observations import get_observation_repository
from app.api.recovery import get_recovery_repository
from app.domain.models import DiagnosticAction, EscalationPackage, EvidenceItem, Observation, PossibleExplanation, SupportCase
from app.domain.recovery import RecoveryValidation
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_escalation_repository import SQLiteEscalationRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_explanation_repository import SQLiteExplanationRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository
from app.persistence.sqlite_recovery_repository import SQLiteRecoveryRepository
from app.playbooks.post_login_feature_failure import PlaybookResult, evaluate_post_login_feature_failure


router = APIRouter(prefix="/api/cases/{case_id}/summary", tags=["case-summary"])


class ReadinessItem(BaseModel):
    name: str
    complete: bool
    detail: str


class CaseSummaryResponse(BaseModel):
    case: SupportCase
    evidence: list[EvidenceItem]
    observations: list[Observation]
    explanations: list[PossibleExplanation]
    actions: list[DiagnosticAction]
    recovery_validations: list[RecoveryValidation]
    escalations: list[EscalationPackage]
    playbook: PlaybookResult
    escalation_readiness: list[ReadinessItem]
    next_recommended_action: str


@router.get("", response_model=CaseSummaryResponse)
def get_case_summary(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
    explanation_repository: SQLiteExplanationRepository = Depends(get_explanation_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
    recovery_repository: SQLiteRecoveryRepository = Depends(get_recovery_repository),
    escalation_repository: SQLiteEscalationRepository = Depends(get_escalation_repository),
) -> CaseSummaryResponse:
    support_case = case_repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")

    evidence = evidence_repository.list_for_case(case_id, limit=500)
    observations = observation_repository.list_for_case(case_id, limit=500)
    explanations = explanation_repository.list_for_case(case_id, limit=500)
    actions = action_repository.list_for_case(case_id, limit=500)
    recovery = recovery_repository.list_for_case(case_id, limit=200)
    escalations = escalation_repository.list_for_case(case_id, limit=200)
    playbook = evaluate_post_login_feature_failure(support_case, evidence, observations)

    readiness = [
        ReadinessItem(
            name="Business impact",
            complete=support_case.impact != "unknown",
            detail=support_case.impact,
        ),
        ReadinessItem(
            name="Affected scope",
            complete=support_case.affected_scope != "unknown",
            detail=support_case.affected_scope,
        ),
        ReadinessItem(
            name="Evidence",
            complete=bool(evidence),
            detail=f"{len(evidence)} evidence item(s)",
        ),
        ReadinessItem(
            name="Evidence-backed observations",
            complete=bool(observations),
            detail=f"{len(observations)} observation(s)",
        ),
        ReadinessItem(
            name="Completed diagnostic action",
            complete=any(action.actual_result for action in actions),
            detail=f"{sum(1 for action in actions if action.actual_result)} completed result(s)",
        ),
        ReadinessItem(
            name="Sensitive-data review",
            complete=not any(
                item.sensitivity.value in {"credential_or_secret", "restricted"} and not item.redacted
                for item in evidence
            ),
            detail="Review evidence marked as secret or restricted before sharing.",
        ),
    ]

    if playbook.missing_evidence:
        next_action = playbook.missing_evidence[0]
    elif not any(action.actual_result for action in actions):
        next_action = "Complete and record the result of a safe diagnostic action."
    elif not escalations:
        next_action = "Generate an escalation package for the appropriate receiving team."
    elif support_case.status.value == "recovery_validation" and not recovery:
        next_action = "Record a recovery validation before resolving the case."
    else:
        next_action = "Review the case status and continue the documented investigation workflow."

    return CaseSummaryResponse(
        case=support_case,
        evidence=evidence,
        observations=observations,
        explanations=explanations,
        actions=actions,
        recovery_validations=recovery,
        escalations=escalations,
        playbook=playbook,
        escalation_readiness=readiness,
        next_recommended_action=next_action,
    )
