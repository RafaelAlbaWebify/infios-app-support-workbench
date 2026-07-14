from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.domain.models import CaseStatus, SupportCase
from app.persistence.sqlite_case_repository import SQLiteCaseRepository

router = APIRouter(prefix="/api/cases", tags=["cases"])

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CASE_DATABASE = ROOT_DIR / "runs" / "infios-cases.sqlite3"


class CreateCaseRequest(BaseModel):
    title: str = Field(min_length=1)
    application: str = Field(min_length=1)
    environment: str = "unknown"
    severity: str = "unknown"
    impact: str = "unknown"
    owner: str | None = None
    affected_scope: str = "unknown"


class CaseListResponse(BaseModel):
    cases: list[SupportCase]
    count: int


@lru_cache(maxsize=1)
def get_case_repository() -> SQLiteCaseRepository:
    return SQLiteCaseRepository(DEFAULT_CASE_DATABASE)


@router.post("", response_model=SupportCase, status_code=status.HTTP_201_CREATED)
def create_case(
    request: CreateCaseRequest,
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> SupportCase:
    support_case = SupportCase(
        title=request.title,
        application=request.application,
        environment=request.environment,
        status=CaseStatus.NEW,
        severity=request.severity,
        impact=request.impact,
        owner=request.owner,
        affected_scope=request.affected_scope,
    )
    return repository.save(support_case)


@router.get("", response_model=CaseListResponse)
def list_cases(
    limit: int = Query(default=50, ge=1, le=200),
    query: str | None = Query(default=None, max_length=200),
    case_status: CaseStatus | None = Query(default=None, alias="status"),
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> CaseListResponse:
    cases, count = repository.search(limit=limit, query=query, status=case_status)
    return CaseListResponse(cases=cases, count=count)


@router.get("/{case_id}", response_model=SupportCase)
def get_case(
    case_id: str,
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> SupportCase:
    support_case = repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    return support_case
