from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.observations import get_observation_repository
from app.domain.models import EvidenceItem, Observation, SupportCase
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository
from app.playbooks.authentication_failure import evaluate_authentication_failure
from app.playbooks.authorization_failure import evaluate_authorization_failure
from app.playbooks.performance_degradation import evaluate_performance_degradation
from app.playbooks.post_login_feature_failure import (
    PlaybookResult,
    evaluate_post_login_feature_failure,
)
from app.playbooks.service_unavailable import evaluate_service_unavailable

router = APIRouter(prefix="/api/cases/{case_id}/playbooks", tags=["playbooks"])
PlaybookEvaluator = Callable[[SupportCase, list[EvidenceItem], list[Observation]], PlaybookResult]


def _evaluate_case_playbook(
    case_id: str,
    evaluator: PlaybookEvaluator,
    case_repository: SQLiteCaseRepository,
    evidence_repository: SQLiteEvidenceRepository,
    observation_repository: SQLiteObservationRepository,
) -> PlaybookResult:
    support_case = case_repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    evidence = evidence_repository.list_for_case(case_id, limit=500)
    observations = observation_repository.list_for_case(case_id, limit=500)
    return evaluator(support_case, evidence, observations)


@router.get("/post-login-feature-failure", response_model=PlaybookResult)
def evaluate_post_login_playbook(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
) -> PlaybookResult:
    return _evaluate_case_playbook(
        case_id,
        evaluate_post_login_feature_failure,
        case_repository,
        evidence_repository,
        observation_repository,
    )


@router.get("/authentication-failure", response_model=PlaybookResult)
def evaluate_authentication_playbook(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
) -> PlaybookResult:
    return _evaluate_case_playbook(
        case_id,
        evaluate_authentication_failure,
        case_repository,
        evidence_repository,
        observation_repository,
    )


@router.get("/authorization-failure", response_model=PlaybookResult)
def evaluate_authorization_playbook(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
) -> PlaybookResult:
    return _evaluate_case_playbook(
        case_id,
        evaluate_authorization_failure,
        case_repository,
        evidence_repository,
        observation_repository,
    )


@router.get("/service-unavailable", response_model=PlaybookResult)
def evaluate_service_unavailable_playbook(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
) -> PlaybookResult:
    return _evaluate_case_playbook(
        case_id,
        evaluate_service_unavailable,
        case_repository,
        evidence_repository,
        observation_repository,
    )


@router.get("/performance-degradation", response_model=PlaybookResult)
def evaluate_performance_degradation_playbook(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
) -> PlaybookResult:
    return _evaluate_case_playbook(
        case_id,
        evaluate_performance_degradation,
        case_repository,
        evidence_repository,
        observation_repository,
    )
