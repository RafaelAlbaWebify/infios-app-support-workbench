from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.problem_actions import get_problem_action_repository
from app.api.problem_rca import get_problem_rca_repository
from app.api.problems import get_problem_repository
from app.persistence.sqlite_problem_action_repository import SQLiteProblemActionRepository
from app.persistence.sqlite_problem_rca_repository import SQLiteProblemRCARepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_lifecycle import transition_problem_status
from app.problem_models import ProblemRecord, ProblemStatus
from app.problem_readiness import build_problem_closure_readiness

router = APIRouter(prefix="/api/problems/{problem_id}/status", tags=["problem-lifecycle"])


class ProblemStatusChangeRequest(BaseModel):
    to_status: ProblemStatus
    changed_by: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2000)


@router.post("", response_model=ProblemRecord)
def change_problem_status(
    problem_id: str,
    request: ProblemStatusChangeRequest,
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    rca_repository: SQLiteProblemRCARepository = Depends(get_problem_rca_repository),
    action_repository: SQLiteProblemActionRepository = Depends(get_problem_action_repository),
) -> ProblemRecord:
    problem = problem_repository.get(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem record not found")

    closure_ready = False
    if request.to_status is ProblemStatus.CLOSED:
        readiness = build_problem_closure_readiness(
            problem_id=problem_id,
            rca_statements=rca_repository.list_for_problem(problem_id),
            actions=action_repository.list_for_problem(problem_id),
        )
        closure_ready = readiness.ready_for_operator_review
        if not closure_ready:
            raise HTTPException(
                status_code=409,
                detail={"message": "Problem closure readiness has blockers", "blockers": readiness.blockers},
            )

    try:
        updated = transition_problem_status(
            problem,
            to_status=request.to_status,
            changed_by=request.changed_by,
            reason=request.reason,
            closure_ready=closure_ready,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return problem_repository.save(updated)
