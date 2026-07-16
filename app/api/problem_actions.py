from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError

from app.api.cases import DEFAULT_CASE_DATABASE
from app.api.problems import get_problem_repository
from app.persistence.sqlite_problem_action_repository import SQLiteProblemActionRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_action_models import (
    ProblemActionSafety,
    ProblemActionStatus,
    ProblemActionType,
    ProblemCorrectiveAction,
)


router = APIRouter(prefix="/api/problems/{problem_id}/actions", tags=["problem-actions"])


class CreateProblemActionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    action_type: ProblemActionType
    safety: ProblemActionSafety
    owner: str = Field(min_length=1, max_length=200)
    created_by: str = Field(min_length=1, max_length=200)
    due_date: str | None = None
    requires_write_or_restart: bool = False


class UpdateProblemActionStatusRequest(BaseModel):
    status: ProblemActionStatus
    implementation_evidence_reference: str | None = Field(default=None, max_length=500)
    validation_result: str | None = Field(default=None, max_length=4000)
    completed_by: str | None = Field(default=None, max_length=200)


class ProblemActionListResponse(BaseModel):
    actions: list[ProblemCorrectiveAction]
    count: int


@lru_cache(maxsize=1)
def get_problem_action_repository() -> SQLiteProblemActionRepository:
    return SQLiteProblemActionRepository(DEFAULT_CASE_DATABASE)


def _require_problem(problem_id: str, repository: SQLiteProblemRepository) -> None:
    if repository.get(problem_id) is None:
        raise HTTPException(status_code=404, detail="Problem record not found")


@router.post("", response_model=ProblemCorrectiveAction, status_code=status.HTTP_201_CREATED)
def create_problem_action(
    problem_id: str,
    request: CreateProblemActionRequest,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    repository: SQLiteProblemActionRepository = Depends(get_problem_action_repository),
) -> ProblemCorrectiveAction:
    _require_problem(problem_id, problem_repository)
    try:
        action = ProblemCorrectiveAction(problem_id=problem_id, **request.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="; ".join(error["msg"] for error in exc.errors())) from exc
    return repository.save(action)


@router.get("", response_model=ProblemActionListResponse)
def list_problem_actions(
    problem_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    repository: SQLiteProblemActionRepository = Depends(get_problem_action_repository),
) -> ProblemActionListResponse:
    _require_problem(problem_id, problem_repository)
    actions = repository.list_for_problem(problem_id, limit=limit)
    return ProblemActionListResponse(actions=actions, count=len(actions))


@router.post("/{action_id}/status", response_model=ProblemCorrectiveAction)
def update_problem_action_status(
    problem_id: str,
    action_id: str,
    request: UpdateProblemActionStatusRequest,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    repository: SQLiteProblemActionRepository = Depends(get_problem_action_repository),
) -> ProblemCorrectiveAction:
    _require_problem(problem_id, problem_repository)
    action = repository.get(action_id)
    if action is None or action.problem_id != problem_id:
        raise HTTPException(status_code=404, detail="Problem corrective action not found")

    completion_statuses = {ProblemActionStatus.IMPLEMENTED, ProblemActionStatus.VALIDATED}
    completed_at = datetime.now(timezone.utc) if request.status in completion_statuses else action.completed_at
    try:
        updated = ProblemCorrectiveAction.model_validate(
            {
                **action.model_dump(),
                **request.model_dump(exclude_none=True),
                "completed_at": completed_at,
                "updated_at": datetime.now(timezone.utc),
            }
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="; ".join(error["msg"] for error in exc.errors())) from exc
    return repository.save(updated)
