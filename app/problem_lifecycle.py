from __future__ import annotations

from datetime import datetime, timezone

from app.problem_models import ProblemRecord, ProblemStatus, ProblemStatusChange


_ALLOWED_TRANSITIONS: dict[ProblemStatus, set[ProblemStatus]] = {
    ProblemStatus.OPEN: {ProblemStatus.INVESTIGATING, ProblemStatus.KNOWN_ERROR, ProblemStatus.RESOLVED},
    ProblemStatus.INVESTIGATING: {ProblemStatus.OPEN, ProblemStatus.KNOWN_ERROR, ProblemStatus.RESOLVED},
    ProblemStatus.KNOWN_ERROR: {ProblemStatus.INVESTIGATING, ProblemStatus.RESOLVED},
    ProblemStatus.RESOLVED: {ProblemStatus.INVESTIGATING, ProblemStatus.CLOSED},
    ProblemStatus.CLOSED: {ProblemStatus.INVESTIGATING},
}


def transition_problem_status(
    problem: ProblemRecord,
    *,
    to_status: ProblemStatus,
    changed_by: str,
    reason: str,
    closure_ready: bool = False,
) -> ProblemRecord:
    if to_status is problem.status:
        raise ValueError("Problem is already in the requested status")
    if to_status not in _ALLOWED_TRANSITIONS[problem.status]:
        raise ValueError(f"Transition from {problem.status.value} to {to_status.value} is not allowed")
    if to_status is ProblemStatus.CLOSED and not closure_ready:
        raise ValueError("Problem closure readiness has blockers")

    changed_at = datetime.now(timezone.utc)
    event = ProblemStatusChange(
        from_status=problem.status,
        to_status=to_status,
        changed_by=changed_by,
        reason=reason,
        changed_at=changed_at,
    )
    return problem.model_copy(
        update={
            "status": to_status,
            "status_history": [*problem.status_history, event],
            "updated_at": changed_at,
        }
    )
