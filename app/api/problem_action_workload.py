from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.problem_actions import get_problem_action_repository
from app.api.problems import get_problem_repository
from app.persistence.sqlite_problem_action_repository import SQLiteProblemActionRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_action_workload import ProblemActionWorkloadReport, build_problem_action_workload_report


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/problem-action-workload", response_model=ProblemActionWorkloadReport)
def problem_action_workload(
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    action_repository: SQLiteProblemActionRepository = Depends(get_problem_action_repository),
) -> ProblemActionWorkloadReport:
    actions = []
    for problem in problem_repository.list(active_only=False):
        actions.extend(action_repository.list_for_problem(problem.problem_id))
    return build_problem_action_workload_report(actions)
