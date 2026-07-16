from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.domain.models import CaseStatus, SupportCase
from app.problem_models import ProblemRecord, ProblemStatus


class OperationalAnalyticsSnapshot(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    case_total: int
    active_case_total: int
    archived_case_total: int
    demo_case_total: int
    real_case_total: int
    unassigned_case_total: int
    case_status_counts: dict[str, int]
    case_severity_counts: dict[str, int]
    application_counts: dict[str, int]
    problem_total: int
    active_problem_total: int
    closed_problem_total: int
    recurring_problem_total: int
    problem_status_counts: dict[str, int]
    disclaimer: str = (
        "Counts and groupings describe stored operational records. They do not establish causation, "
        "service quality, team performance, or incident severity beyond the recorded metadata."
    )


def _sorted_counts(values: list[str]) -> dict[str, int]:
    counts = Counter(value.strip() or "unknown" for value in values)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0].lower())))


def build_operational_snapshot(
    cases: list[SupportCase], problems: list[ProblemRecord]
) -> OperationalAnalyticsSnapshot:
    active_cases = [case for case in cases if case.archived_at is None]
    active_problem_statuses = {
        ProblemStatus.OPEN,
        ProblemStatus.INVESTIGATING,
        ProblemStatus.KNOWN_ERROR,
    }
    return OperationalAnalyticsSnapshot(
        case_total=len(cases),
        active_case_total=len(active_cases),
        archived_case_total=sum(case.archived_at is not None for case in cases),
        demo_case_total=sum(case.is_demo for case in cases),
        real_case_total=sum(not case.is_demo for case in cases),
        unassigned_case_total=sum(not case.owner or not case.owner.strip() for case in active_cases),
        case_status_counts=_sorted_counts([case.status.value for case in cases]),
        case_severity_counts=_sorted_counts([case.severity for case in cases]),
        application_counts=_sorted_counts([case.application for case in cases]),
        problem_total=len(problems),
        active_problem_total=sum(problem.status in active_problem_statuses for problem in problems),
        closed_problem_total=sum(
            problem.status in {ProblemStatus.RESOLVED, ProblemStatus.CLOSED} for problem in problems
        ),
        recurring_problem_total=sum(problem.occurrence_count > 1 for problem in problems),
        problem_status_counts=_sorted_counts([problem.status.value for problem in problems]),
    )
