from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone

from pydantic import BaseModel

from app.problem_action_models import ProblemActionStatus, ProblemCorrectiveAction


class ProblemActionWorkloadItem(BaseModel):
    action_id: str
    problem_id: str
    title: str
    owner: str
    status: ProblemActionStatus
    due_date: date | None
    overdue: bool
    validation_pending: bool


class ProblemActionWorkloadReport(BaseModel):
    generated_at: datetime
    total_action_count: int
    active_action_count: int
    overdue_action_count: int
    blocked_action_count: int
    validation_pending_count: int
    actions_by_status: dict[str, int]
    actions_by_owner: dict[str, int]
    attention_items: list[ProblemActionWorkloadItem]
    disclaimer: str


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0].lower())))


def build_problem_action_workload_report(
    actions: list[ProblemCorrectiveAction], *, today: date | None = None
) -> ProblemActionWorkloadReport:
    current_date = today or datetime.now(timezone.utc).date()
    active_statuses = {
        ProblemActionStatus.PLANNED,
        ProblemActionStatus.IN_PROGRESS,
        ProblemActionStatus.IMPLEMENTED,
        ProblemActionStatus.BLOCKED,
    }
    status_counts: Counter[str] = Counter(action.status.value for action in actions)
    owner_counts: Counter[str] = Counter(action.owner for action in actions if action.status is not ProblemActionStatus.CANCELLED)
    attention: list[ProblemActionWorkloadItem] = []
    overdue_count = blocked_count = validation_pending_count = 0

    for action in actions:
        if action.status is ProblemActionStatus.CANCELLED:
            continue
        overdue = action.due_date is not None and action.due_date < current_date and action.status is not ProblemActionStatus.VALIDATED
        validation_pending = action.status is ProblemActionStatus.IMPLEMENTED
        if overdue:
            overdue_count += 1
        if action.status is ProblemActionStatus.BLOCKED:
            blocked_count += 1
        if validation_pending:
            validation_pending_count += 1
        if overdue or validation_pending or action.status is ProblemActionStatus.BLOCKED:
            attention.append(
                ProblemActionWorkloadItem(
                    action_id=action.action_id,
                    problem_id=action.problem_id,
                    title=action.title,
                    owner=action.owner,
                    status=action.status,
                    due_date=action.due_date,
                    overdue=overdue,
                    validation_pending=validation_pending,
                )
            )

    attention.sort(key=lambda item: (not item.overdue, item.due_date or date.max, item.owner.lower(), item.title.lower()))
    return ProblemActionWorkloadReport(
        generated_at=datetime.now(timezone.utc),
        total_action_count=len(actions),
        active_action_count=sum(action.status in active_statuses for action in actions),
        overdue_action_count=overdue_count,
        blocked_action_count=blocked_count,
        validation_pending_count=validation_pending_count,
        actions_by_status=_ordered(status_counts),
        actions_by_owner=_ordered(owner_counts),
        attention_items=attention,
        disclaimer=(
            "This report identifies stored action workload and due-date conditions only. "
            "It does not change action or problem status, assess operator performance, or prove risk reduction."
        ),
    )
