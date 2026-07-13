from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.observations import get_observation_repository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository
from app.playbooks.post_login_feature_failure import (
    PlaybookResult,
    evaluate_post_login_feature_failure,
)


router = APIRouter(prefix="/api/cases/{case_id}/playbooks", tags=["playbooks"])


@router.get("/post-login-feature-failure", response_model=PlaybookResult)
def evaluate_playbook(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
) -> PlaybookResult:
    support_case = case_repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    evidence = evidence_repository.list_for_case(case_id, limit=500)
    observations = observation_repository.list_for_case(case_id, limit=500)
    return evaluate_post_login_feature_failure(support_case, evidence, observations)
