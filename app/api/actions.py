from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.domain.models import (
    ActionSafetyLevel,
    ActionStatus,
    DiagnosticAction,
)
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


router = APIRouter(prefix="/api/cases/{case_id}/actions", tags=["actions"])


class CreateActionRequest(BaseModel):
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    safety_level: ActionSafetyLevel
    requires_write_or_restart: bool = False
    expected_result: str | None = None


class CompleteActionRequest(BaseModel):
    actual_result: str = Field(min_length=1)
    conclusion: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    performed_by: str | None = None


class ActionListResponse(BaseModel):
    actions: list[DiagnosticAction]
    count: int


@lru_cache(maxsize=1)
def get_action_repository() -> SQLiteActionRepository:
    return SQLiteActionRepository(DEFAULT_CASE_DATABASE)


def _require_case(case_id: str, repository: SQLiteCaseRepository) -> None:
    if repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")


@router.post("", response_model=DiagnosticAction, status_code=status.HTTP_201_CREATED)
def create_action(
    case_id: str,
    request: CreateActionRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
) -> DiagnosticAction:
    _require_case(case_id, case_repository)
    action = DiagnosticAction(
        case_id=case_id,
        name=request.name,
        purpose=request.purpose,
        safety_level=request.safety_level,
        requires_write_or_restart=request.requires_write_or_restart,
        expected_result=request.expected_result,
        status=ActionStatus.RECOMMENDED,
    )
    return action_repository.save(action)


@router.get("", response_model=ActionListResponse)
def list_actions(
    case_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
) -> ActionListResponse:
    _require_case(case_id, case_repository)
    actions = action_repository.list_for_case(case_id, limit=limit)
    return ActionListResponse(actions=actions, count=len(actions))


@router.get("/{action_id}", response_model=DiagnosticAction)
def get_action(
    case_id: str,
    action_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
) -> DiagnosticAction:
    _require_case(case_id, case_repository)
    action = action_repository.get(action_id)
    if action is None or action.case_id != case_id:
        raise HTTPException(status_code=404, detail="Diagnostic action not found")
    return action


@router.post("/{action_id}/start", response_model=DiagnosticAction)
def start_action(
    case_id: str,
    action_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
) -> DiagnosticAction:
    _require_case(case_id, case_repository)
    action = action_repository.get(action_id)
    if action is None or action.case_id != case_id:
        raise HTTPException(status_code=404, detail="Diagnostic action not found")
    updated = action.model_copy(
        update={"status": ActionStatus.IN_PROGRESS, "started_at": datetime.now(timezone.utc)}
    )
    return action_repository.save(updated)


@router.post("/{action_id}/complete", response_model=DiagnosticAction)
def complete_action(
    case_id: str,
    action_id: str,
    request: CompleteActionRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
) -> DiagnosticAction:
    _require_case(case_id, case_repository)
    action = action_repository.get(action_id)
    if action is None or action.case_id != case_id:
        raise HTTPException(status_code=404, detail="Diagnostic action not found")
    now = datetime.now(timezone.utc)
    updated = action.model_copy(
        update={
            "status": ActionStatus.COMPLETED,
            "started_at": action.started_at or now,
            "completed_at": now,
            "actual_result": request.actual_result,
            "conclusion": request.conclusion,
            "evidence_ids": list(dict.fromkeys(request.evidence_ids)),
            "performed_by": request.performed_by,
        }
    )
    return action_repository.save(updated)
