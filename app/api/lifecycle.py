from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.cases import get_case_repository
from app.domain.models import CaseStatus, SupportCase
from app.persistence.sqlite_case_repository import SQLiteCaseRepository

router = APIRouter(prefix="/api/cases/{case_id}/status", tags=["case-lifecycle"])

_ALLOWED_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.NEW: {CaseStatus.INFORMATION_GATHERING, CaseStatus.CLOSED},
    CaseStatus.INFORMATION_GATHERING: {
        CaseStatus.INVESTIGATION,
        CaseStatus.WAITING_FOR_USER,
        CaseStatus.BLOCKED,
        CaseStatus.CLOSED,
    },
    CaseStatus.INVESTIGATION: {
        CaseStatus.WAITING_FOR_USER,
        CaseStatus.WAITING_FOR_ESCALATION,
        CaseStatus.WAITING_FOR_ANOTHER_TEAM,
        CaseStatus.BLOCKED,
        CaseStatus.RECOVERY_VALIDATION,
    },
    CaseStatus.WAITING_FOR_USER: {CaseStatus.INFORMATION_GATHERING, CaseStatus.INVESTIGATION, CaseStatus.CLOSED},
    CaseStatus.WAITING_FOR_ESCALATION: {CaseStatus.ESCALATED, CaseStatus.INVESTIGATION},
    CaseStatus.ESCALATED: {CaseStatus.WAITING_FOR_ANOTHER_TEAM, CaseStatus.INVESTIGATION, CaseStatus.RECOVERY_VALIDATION},
    CaseStatus.WAITING_FOR_ANOTHER_TEAM: {CaseStatus.INVESTIGATION, CaseStatus.RECOVERY_VALIDATION, CaseStatus.BLOCKED},
    CaseStatus.BLOCKED: {CaseStatus.INFORMATION_GATHERING, CaseStatus.INVESTIGATION, CaseStatus.CLOSED},
    CaseStatus.RECOVERY_VALIDATION: {CaseStatus.INVESTIGATION, CaseStatus.RESOLVED},
    CaseStatus.RESOLVED: {CaseStatus.RECOVERY_VALIDATION, CaseStatus.CLOSED},
    CaseStatus.CLOSED: set(),
}


class StatusTransitionRequest(BaseModel):
    status: CaseStatus


@router.post("", response_model=SupportCase)
def transition_case_status(
    case_id: str,
    request: StatusTransitionRequest,
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> SupportCase:
    support_case = repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    if request.status == support_case.status:
        return support_case
    if request.status not in _ALLOWED_TRANSITIONS[support_case.status]:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid case transition: {support_case.status.value} -> {request.status.value}",
        )
    updated = support_case.model_copy(
        update={"status": request.status, "updated_at": datetime.now(timezone.utc)}
    )
    return repository.save(updated)
