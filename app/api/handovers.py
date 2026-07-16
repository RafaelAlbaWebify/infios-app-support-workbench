from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.handover_models import HandoverCaseItem, ShiftHandover
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_handover_repository import SQLiteHandoverRepository


router = APIRouter(prefix="/api/handovers", tags=["handovers"])


class CreateHandoverRequest(BaseModel):
    shift_label: str = Field(min_length=1, max_length=200)
    prepared_by: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    cases: list[HandoverCaseItem] = Field(min_length=1, max_length=100)


class HandoverListResponse(BaseModel):
    handovers: list[ShiftHandover]
    count: int


@lru_cache(maxsize=1)
def get_handover_repository() -> SQLiteHandoverRepository:
    return SQLiteHandoverRepository(DEFAULT_CASE_DATABASE)


@router.post("", response_model=ShiftHandover, status_code=status.HTTP_201_CREATED)
def create_handover(
    request: CreateHandoverRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    repository: SQLiteHandoverRepository = Depends(get_handover_repository),
) -> ShiftHandover:
    missing_case_ids = [item.case_id for item in request.cases if case_repository.get(item.case_id) is None]
    if missing_case_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "All handover case references must exist.",
                "missing_case_ids": sorted(set(missing_case_ids)),
            },
        )
    return repository.save(ShiftHandover(**request.model_dump()))


@router.get("", response_model=HandoverListResponse)
def list_handovers(
    limit: int = Query(default=50, ge=1, le=200),
    repository: SQLiteHandoverRepository = Depends(get_handover_repository),
) -> HandoverListResponse:
    handovers = repository.list_recent(limit=limit)
    return HandoverListResponse(handovers=handovers, count=len(handovers))


@router.get("/{handover_id}", response_model=ShiftHandover)
def get_handover(
    handover_id: str,
    repository: SQLiteHandoverRepository = Depends(get_handover_repository),
) -> ShiftHandover:
    handover = repository.get(handover_id)
    if handover is None:
        raise HTTPException(status_code=404, detail="Shift handover not found")
    return handover
