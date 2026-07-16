from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.domain.models import CaseStatus, SupportCase


class DailyCaseActivity(BaseModel):
    date: str
    created: int = 0
    updated: int = 0
    resolved_or_closed: int = 0


class OperationalTrendReport(BaseModel):
    generated_at: datetime
    window_days: int = Field(ge=1, le=365)
    window_start: datetime
    window_end: datetime
    included_case_count: int
    created_case_count: int
    updated_case_count: int
    resolved_or_closed_count: int
    daily_activity: list[DailyCaseActivity]
    created_by_application: dict[str, int]
    created_by_severity: dict[str, int]
    disclaimer: str


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0].lower())))


def build_operational_trend_report(
    cases: list[SupportCase], *, window_days: int, now: datetime | None = None
) -> OperationalTrendReport:
    if not 1 <= window_days <= 365:
        raise ValueError("window_days must be between 1 and 365")
    end = now or datetime.now(timezone.utc)
    start = end - timedelta(days=window_days)
    dates = [(start + timedelta(days=index)).date().isoformat() for index in range(window_days + 1)]
    activity = {date: DailyCaseActivity(date=date) for date in dates}
    created_apps: Counter[str] = Counter()
    created_severities: Counter[str] = Counter()
    created_count = updated_count = resolved_count = 0

    for case in cases:
        if start <= case.created_at <= end:
            created_count += 1
            created_apps[case.application] += 1
            created_severities[case.severity] += 1
            key = case.created_at.date().isoformat()
            if key in activity:
                activity[key].created += 1
        if start <= case.updated_at <= end:
            updated_count += 1
            key = case.updated_at.date().isoformat()
            if key in activity:
                activity[key].updated += 1
                if case.status in {CaseStatus.RESOLVED, CaseStatus.CLOSED}:
                    activity[key].resolved_or_closed += 1
                    resolved_count += 1

    return OperationalTrendReport(
        generated_at=end,
        window_days=window_days,
        window_start=start,
        window_end=end,
        included_case_count=len(cases),
        created_case_count=created_count,
        updated_case_count=updated_count,
        resolved_or_closed_count=resolved_count,
        daily_activity=list(activity.values()),
        created_by_application=_ordered(created_apps),
        created_by_severity=_ordered(created_severities),
        disclaimer=(
            "These trends describe timestamps and metadata stored in the workbench. "
            "They do not measure team performance, service reliability, or incident causation."
        ),
    )
