from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.cases import get_case_repository
from app.operational_trends import OperationalTrendReport, build_operational_trend_report
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/operational-trends", response_model=OperationalTrendReport)
def operational_trends(
    window_days: int = Query(default=30, ge=1, le=365),
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> OperationalTrendReport:
    cases, _ = case_repository.search(limit=10000, archive_state="all", case_kind="real")
    return build_operational_trend_report(cases, window_days=window_days)
