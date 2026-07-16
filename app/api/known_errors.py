from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError

from app.api.cases import DEFAULT_CASE_DATABASE
from app.api.problems import get_problem_repository
from app.known_error_models import KnownErrorRecord, KnownErrorStatus, WorkaroundSafety
from app.persistence.sqlite_known_error_repository import SQLiteKnownErrorRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository


router = APIRouter(prefix="/api/problems/{problem_id}/known-errors", tags=["known-errors"])


class CreateKnownErrorRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    symptom_summary: str = Field(min_length=1, max_length=4000)
    workaround_steps: list[str] = Field(min_length=1, max_length=100)
    workaround_limitations: str = Field(min_length=1, max_length=4000)
    validation_guidance: str = Field(min_length=1, max_length=4000)
    safety: WorkaroundSafety
    requires_write_or_restart: bool = False
    owner: str = Field(min_length=1, max_length=200)
    created_by: str = Field(min_length=1, max_length=200)


class PublishKnownErrorRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=200)
    approval_reason: str = Field(min_length=1, max_length=2000)


class KnownErrorListResponse(BaseModel):
    records: list[KnownErrorRecord]
    count: int


@lru_cache(maxsize=1)
def get_known_error_repository() -> SQLiteKnownErrorRepository:
    return SQLiteKnownErrorRepository(DEFAULT_CASE_DATABASE)


def _require_problem(problem_id: str, repository: SQLiteProblemRepository) -> None:
    if repository.get(problem_id) is None:
        raise HTTPException(status_code=404, detail="Problem record not found")


@router.post("", response_model=KnownErrorRecord, status_code=status.HTTP_201_CREATED)
def create_known_error(
    problem_id: str,
    request: CreateKnownErrorRequest,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    repository: SQLiteKnownErrorRepository = Depends(get_known_error_repository),
) -> KnownErrorRecord:
    _require_problem(problem_id, problem_repository)
    try:
        record = KnownErrorRecord(problem_id=problem_id, **request.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="; ".join(error["msg"] for error in exc.errors())) from exc
    return repository.save(record)


@router.get("", response_model=KnownErrorListResponse)
def list_known_errors(
    problem_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    repository: SQLiteKnownErrorRepository = Depends(get_known_error_repository),
) -> KnownErrorListResponse:
    _require_problem(problem_id, problem_repository)
    records = repository.list_for_problem(problem_id, limit=limit)
    return KnownErrorListResponse(records=records, count=len(records))


@router.post("/{known_error_id}/publish", response_model=KnownErrorRecord)
def publish_known_error(
    problem_id: str,
    known_error_id: str,
    request: PublishKnownErrorRequest,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    repository: SQLiteKnownErrorRepository = Depends(get_known_error_repository),
) -> KnownErrorRecord:
    _require_problem(problem_id, problem_repository)
    record = repository.get(known_error_id)
    if record is None or record.problem_id != problem_id:
        raise HTTPException(status_code=404, detail="Known error record not found")
    if record.status is not KnownErrorStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Only draft known errors can be published")
    now = datetime.now(timezone.utc)
    updated = KnownErrorRecord.model_validate({
        **record.model_dump(),
        "status": KnownErrorStatus.PUBLISHED,
        "approved_by": request.approved_by,
        "approval_reason": request.approval_reason,
        "approved_at": now,
        "updated_at": now,
    })
    return repository.save(updated)


@router.post("/{known_error_id}/retire", response_model=KnownErrorRecord)
def retire_known_error(
    problem_id: str,
    known_error_id: str,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    repository: SQLiteKnownErrorRepository = Depends(get_known_error_repository),
) -> KnownErrorRecord:
    _require_problem(problem_id, problem_repository)
    record = repository.get(known_error_id)
    if record is None or record.problem_id != problem_id:
        raise HTTPException(status_code=404, detail="Known error record not found")
    if record.status is not KnownErrorStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="Only published known errors can be retired")
    updated = record.model_copy(update={"status": KnownErrorStatus.RETIRED, "updated_at": datetime.now(timezone.utc)})
    return repository.save(updated)
