from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.cases import get_case_repository
from app.api.problems import get_problem_repository
from app.operational_analytics import OperationalAnalyticsSnapshot, build_operational_snapshot
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/operational-snapshot", response_model=OperationalAnalyticsSnapshot)
def operational_snapshot(
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
) -> OperationalAnalyticsSnapshot:
    cases, _ = case_repository.search(limit=10000, archive_state="all")
    problems = problem_repository.list(active_only=False)
    return build_operational_snapshot(cases, problems)
