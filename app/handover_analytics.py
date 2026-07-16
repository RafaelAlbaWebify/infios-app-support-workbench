from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from app.handover_models import ShiftHandover


DISCLAIMER = (
    "Handover activity describes stored operator-authored snapshots only. "
    "Counts do not measure operator performance, handover quality, incident severity, or root cause."
)


class HandoverDailyActivity(BaseModel):
    date: str
    handovers: int = 0
    case_references: int = 0
    attention_references: int = 0
    blocker_references: int = 0


class HandoverActivityReport(BaseModel):
    generated_at: datetime
    window_days: int = Field(ge=1, le=365)
    window_start: datetime
    window_end: datetime
    total_handovers: int
    total_case_references: int
    unique_case_count: int
    attention_references: int
    blocker_references: int
    shift_label_counts: dict[str, int]
    daily_activity: list[HandoverDailyActivity]
    disclaimer: str = DISCLAIMER


def _ordered_counts(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0].lower())))


def build_handover_activity_report(
    handovers: list[ShiftHandover], *, window_days: int, now: datetime | None = None
) -> HandoverActivityReport:
    if not 1 <= window_days <= 365:
        raise ValueError("window_days must be between 1 and 365")
    end = now or datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    start = end - timedelta(days=window_days)
    selected = [handover for handover in handovers if start <= handover.created_at <= end]

    daily: dict[str, HandoverDailyActivity] = {}
    shift_labels: Counter[str] = Counter()
    unique_case_ids: set[str] = set()
    case_references = attention_references = blocker_references = 0

    for handover in selected:
        date_key = handover.created_at.date().isoformat()
        bucket = daily.setdefault(date_key, HandoverDailyActivity(date=date_key))
        bucket.handovers += 1
        shift_labels[handover.shift_label] += 1
        for item in handover.cases:
            case_references += 1
            unique_case_ids.add(item.case_id)
            bucket.case_references += 1
            if item.attention_required:
                attention_references += 1
                bucket.attention_references += 1
            if item.blocker:
                blocker_references += 1
                bucket.blocker_references += 1

    return HandoverActivityReport(
        generated_at=end,
        window_days=window_days,
        window_start=start,
        window_end=end,
        total_handovers=len(selected),
        total_case_references=case_references,
        unique_case_count=len(unique_case_ids),
        attention_references=attention_references,
        blocker_references=blocker_references,
        shift_label_counts=_ordered_counts(shift_labels),
        daily_activity=[daily[key] for key in sorted(daily)],
    )
