from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_models import ProblemRecord, ProblemStatus


router = APIRouter(prefix="/api/problems", tags=["problems"])


class CreateProblemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    status: ProblemStatus = ProblemStatus.OPEN
    owner: str = Field(min_length=1, max_length=200)
    created_by: str = Field(min_length=1, max_length=200)
    case_ids: list[str] = Field(min_length=1, max_length=200)
    recurrence_notes: str | None = Field(default=None, max_length=4000)


class ProblemListResponse(BaseModel):
    problems: list[ProblemRecord]
    count: int


@lru_cache(maxsize=1)
def get_problem_repository() -> SQLiteProblemRepository:
    return SQLiteProblemRepository(DEFAULT_CASE_DATABASE)


def _validate_case_ids(case_ids: list[str], repository: SQLiteCaseRepository) -> list[str]:
    invalid = [case_id for case_id in case_ids if repository.get(case_id) is None]
    if invalid:
        raise HTTPException(status_code=422, detail={"invalid_case_ids": invalid})
    return case_ids


@router.post("", response_model=ProblemRecord, status_code=status.HTTP_201_CREATED)
def create_problem(
    request: CreateProblemRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
) -> ProblemRecord:
    case_ids = _validate_case_ids(request.case_ids, case_repository)
    problem = ProblemRecord(**{**request.model_dump(), "case_ids": case_ids})
    return problem_repository.save(problem)


@router.get("", response_model=ProblemListResponse)
def list_problems(
    active_only: bool = Query(default=True),
    repository: SQLiteProblemRepository = Depends(get_problem_repository),
) -> ProblemListResponse:
    problems = repository.list(active_only=active_only)
    return ProblemListResponse(problems=problems, count=len(problems))


@router.get("/{problem_id}", response_model=ProblemRecord)
def get_problem(
    problem_id: str,
    repository: SQLiteProblemRepository = Depends(get_problem_repository),
) -> ProblemRecord:
    problem = repository.get(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem record not found")
    return problem
