from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from app.problem_action_models import ProblemActionStatus, ProblemCorrectiveAction
from app.problem_rca_models import ProblemRCAStatement, RCAStatus


class ProblemClosureReadinessReport(BaseModel):
    problem_id: str
    status: str
    ready_for_operator_review: bool
    confirmed_rca_count: int
    total_action_count: int
    validated_action_count: int
    open_action_count: int
    overdue_action_count: int
    blockers: list[str]


def build_problem_closure_readiness(
    *,
    problem_id: str,
    rca_statements: list[ProblemRCAStatement],
    actions: list[ProblemCorrectiveAction],
    today: date | None = None,
) -> ProblemClosureReadinessReport:
    today = today or date.today()
    confirmed_rca_count = sum(statement.status is RCAStatus.CONFIRMED for statement in rca_statements)
    relevant_actions = [action for action in actions if action.status is not ProblemActionStatus.CANCELLED]
    validated_action_count = sum(action.status is ProblemActionStatus.VALIDATED for action in relevant_actions)
    open_actions = [action for action in relevant_actions if action.status is not ProblemActionStatus.VALIDATED]
    overdue_action_count = sum(
        action.due_date is not None and action.due_date < today for action in open_actions
    )

    blockers: list[str] = []
    if confirmed_rca_count == 0:
        blockers.append("no_confirmed_rca")
    if not relevant_actions:
        blockers.append("no_corrective_actions")
    if open_actions:
        blockers.append("actions_not_validated")
    if any(action.status is ProblemActionStatus.BLOCKED for action in relevant_actions):
        blockers.append("blocked_actions")
    if overdue_action_count:
        blockers.append("overdue_actions")

    ready = not blockers
    return ProblemClosureReadinessReport(
        problem_id=problem_id,
        status="ready" if ready else "not_ready",
        ready_for_operator_review=ready,
        confirmed_rca_count=confirmed_rca_count,
        total_action_count=len(relevant_actions),
        validated_action_count=validated_action_count,
        open_action_count=len(open_actions),
        overdue_action_count=overdue_action_count,
        blockers=blockers,
    )
