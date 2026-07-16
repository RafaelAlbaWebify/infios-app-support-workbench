from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.handovers import get_handover_repository
from app.handover_analytics import HandoverActivityReport, build_handover_activity_report
from app.persistence.sqlite_handover_repository import SQLiteHandoverRepository


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/handover-activity", response_model=HandoverActivityReport)
def handover_activity(
    window_days: int = Query(default=30, ge=1, le=365),
    repository: SQLiteHandoverRepository = Depends(get_handover_repository),
) -> HandoverActivityReport:
    handovers = repository.list_recent(limit=500)
    return build_handover_activity_report(handovers, window_days=window_days)
