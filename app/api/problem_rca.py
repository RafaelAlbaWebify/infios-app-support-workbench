from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.api.cases import DEFAULT_CASE_DATABASE
from app.api.explanations import get_explanation_repository
from app.api.problems import get_problem_repository
from app.domain.models import ExplanationStatus
from app.persistence.sqlite_explanation_repository import SQLiteExplanationRepository
from app.persistence.sqlite_problem_rca_repository import SQLiteProblemRCARepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_rca_models import ProblemRCAStatement, RCAStatus


router = APIRouter(prefix="/api/problems/{problem_id}/rca", tags=["problem-rca"])


class CreateRCARequest(BaseModel):
    statement: str = Field(min_length=1, max_length=4000)
    supporting_explanation_ids: list[str] = Field(default_factory=list, max_length=200)
    contradicting_explanation_ids: list[str] = Field(default_factory=list, max_length=200)
    created_by: str = Field(min_length=1, max_length=200)


class ConfirmRCARequest(BaseModel):
    confirmed_by: str = Field(min_length=1, max_length=200)
    confirmation_reason: str = Field(min_length=1, max_length=2000)


class RCAListResponse(BaseModel):
    statements: list[ProblemRCAStatement]
    count: int


@lru_cache(maxsize=1)
def get_problem_rca_repository() -> SQLiteProblemRCARepository:
    return SQLiteProblemRCARepository(DEFAULT_CASE_DATABASE)


def _require_problem(problem_id: str, repository: SQLiteProblemRepository):
    problem = repository.get(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem record not found")
    return problem


def _validate_explanations(problem, explanation_ids: list[str], repository: SQLiteExplanationRepository) -> list[str]:
    normalized = list(dict.fromkeys(explanation_ids))
    invalid = []
    for explanation_id in normalized:
        explanation = repository.get(explanation_id)
        if explanation is None or explanation.case_id not in problem.case_ids:
            invalid.append(explanation_id)
    if invalid:
        raise HTTPException(status_code=422, detail={"invalid_explanation_ids": invalid})
    return normalized


@router.post("", response_model=ProblemRCAStatement, status_code=status.HTTP_201_CREATED)
def create_rca(
    problem_id: str,
    request: CreateRCARequest,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    explanation_repository: SQLiteExplanationRepository = Depends(get_explanation_repository),
    rca_repository: SQLiteProblemRCARepository = Depends(get_problem_rca_repository),
) -> ProblemRCAStatement:
    problem = _require_problem(problem_id, problem_repository)
    supporting = _validate_explanations(problem, request.supporting_explanation_ids, explanation_repository)
    contradicting = _validate_explanations(problem, request.contradicting_explanation_ids, explanation_repository)
    try:
        statement = ProblemRCAStatement(
            problem_id=problem_id,
            statement=request.statement,
            supporting_explanation_ids=supporting,
            contradicting_explanation_ids=contradicting,
            created_by=request.created_by,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return rca_repository.save(statement)


@router.get("", response_model=RCAListResponse)
def list_rca(
    problem_id: str,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    rca_repository: SQLiteProblemRCARepository = Depends(get_problem_rca_repository),
) -> RCAListResponse:
    _require_problem(problem_id, problem_repository)
    statements = rca_repository.list_for_problem(problem_id)
    return RCAListResponse(statements=statements, count=len(statements))


@router.post("/{rca_id}/confirm", response_model=ProblemRCAStatement)
def confirm_rca(
    problem_id: str,
    rca_id: str,
    request: ConfirmRCARequest,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    explanation_repository: SQLiteExplanationRepository = Depends(get_explanation_repository),
    rca_repository: SQLiteProblemRCARepository = Depends(get_problem_rca_repository),
) -> ProblemRCAStatement:
    problem = _require_problem(problem_id, problem_repository)
    statement = rca_repository.get(rca_id)
    if statement is None or statement.problem_id != problem_id:
        raise HTTPException(status_code=404, detail="RCA statement not found")
    explanations = []
    for explanation_id in statement.supporting_explanation_ids:
        explanation = explanation_repository.get(explanation_id)
        if explanation is None or explanation.case_id not in problem.case_ids:
            raise HTTPException(status_code=422, detail="Supporting explanation is no longer valid for this problem")
        explanations.append(explanation)
    if not explanations or any(explanation.status is not ExplanationStatus.CONFIRMED for explanation in explanations):
        raise HTTPException(status_code=422, detail="RCA confirmation requires confirmed supporting explanations")
    updated = ProblemRCAStatement.model_validate({
        **statement.model_dump(),
        "status": RCAStatus.CONFIRMED,
        "confirmed_by": request.confirmed_by,
        "confirmation_reason": request.confirmation_reason,
        "confirmed_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    return rca_repository.save(updated)
