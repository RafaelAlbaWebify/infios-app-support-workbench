from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.problem_actions import get_problem_action_repository
from app.api.problem_rca import get_problem_rca_repository
from app.api.problems import get_problem_repository
from app.persistence.sqlite_problem_action_repository import SQLiteProblemActionRepository
from app.persistence.sqlite_problem_rca_repository import SQLiteProblemRCARepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_readiness import ProblemClosureReadinessReport, build_problem_closure_readiness


router = APIRouter(prefix="/api/problems/{problem_id}/closure-readiness", tags=["problem-readiness"])


@router.get("", response_model=ProblemClosureReadinessReport)
def problem_closure_readiness(
    problem_id: str,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    rca_repository: SQLiteProblemRCARepository = Depends(get_problem_rca_repository),
    action_repository: SQLiteProblemActionRepository = Depends(get_problem_action_repository),
) -> ProblemClosureReadinessReport:
    if problem_repository.get(problem_id) is None:
        raise HTTPException(status_code=404, detail="Problem record not found")
    return build_problem_closure_readiness(
        problem_id=problem_id,
        rca_statements=rca_repository.list_for_problem(problem_id),
        actions=action_repository.list_for_problem(problem_id),
    )
