from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.problem_actions import get_problem_action_repository
from app.api.problem_rca import get_problem_rca_repository
from app.api.problems import get_problem_repository
from app.main import app
from app.problem_action_models import ProblemActionSafety, ProblemActionStatus, ProblemActionType, ProblemCorrectiveAction
from app.problem_lifecycle import transition_problem_status
from app.problem_models import ProblemRecord, ProblemStatus
from app.problem_rca_models import ProblemRCAStatement, RCAStatus


class ProblemRepo:
    def __init__(self, problem): self.problem = problem
    def get(self, problem_id): return self.problem if problem_id == self.problem.problem_id else None
    def save(self, problem): self.problem = problem; return problem


class RCARepo:
    def __init__(self, items): self.items = items
    def list_for_problem(self, problem_id): return list(self.items)


class ActionRepo:
    def __init__(self, items): self.items = items
    def list_for_problem(self, problem_id): return list(self.items)


def problem(status=ProblemStatus.OPEN):
    return ProblemRecord(problem_id="problem-1", title="Repeated checkout failure", summary="Stored recurrence", status=status, owner="L2", created_by="L2", case_ids=["case-1", "case-2"])


def test_transition_records_operator_reason_and_timestamp():
    original = problem()
    updated = transition_problem_status(original, to_status=ProblemStatus.INVESTIGATING, changed_by="Rafael", reason="Recurring cases accepted for investigation")
    assert original.status is ProblemStatus.OPEN
    assert updated.status is ProblemStatus.INVESTIGATING
    assert updated.status_history[0].changed_by == "Rafael"
    assert updated.status_history[0].from_status is ProblemStatus.OPEN
    assert updated.updated_at >= original.updated_at


def test_closure_requires_readiness():
    try:
        transition_problem_status(problem(ProblemStatus.RESOLVED), to_status=ProblemStatus.CLOSED, changed_by="L2", reason="Close", closure_ready=False)
    except ValueError as exc:
        assert "readiness" in str(exc)
    else:
        raise AssertionError("Closure should be blocked")


def test_status_endpoint_returns_readiness_blockers_without_mutation():
    repository = ProblemRepo(problem(ProblemStatus.RESOLVED))
    app.dependency_overrides[get_problem_repository] = lambda: repository
    app.dependency_overrides[get_problem_rca_repository] = lambda: RCARepo([])
    app.dependency_overrides[get_problem_action_repository] = lambda: ActionRepo([])
    try:
        response = TestClient(app).post("/api/problems/problem-1/status", json={"to_status": "closed", "changed_by": "Rafael", "reason": "Closure review"})
        assert response.status_code == 409
        assert "no_confirmed_rca" in response.json()["detail"]["blockers"]
        assert repository.problem.status is ProblemStatus.RESOLVED
        assert repository.problem.status_history == []
    finally:
        app.dependency_overrides.clear()


def test_status_endpoint_closes_ready_problem_and_persists_audit():
    now = datetime.now(timezone.utc)
    repository = ProblemRepo(problem(ProblemStatus.RESOLVED))
    rca = ProblemRCAStatement(problem_id="problem-1", statement="Confirmed application defect", status=RCAStatus.CONFIRMED, supporting_explanation_ids=["explanation-1"], created_by="L2", confirmed_by="Rafael", confirmation_reason="Evidence-backed case explanations", confirmed_at=now)
    action = ProblemCorrectiveAction(problem_id="problem-1", title="Deploy correction", description="Approved correction record", action_type=ProblemActionType.CORRECTIVE, status=ProblemActionStatus.VALIDATED, safety=ProblemActionSafety.APPROVED_CHANGE_REQUIRED, owner="Engineering", created_by="L2", implementation_evidence_reference="change-123", validation_result="Affected operation completed successfully", completed_by="Engineering", completed_at=now)
    app.dependency_overrides[get_problem_repository] = lambda: repository
    app.dependency_overrides[get_problem_rca_repository] = lambda: RCARepo([rca])
    app.dependency_overrides[get_problem_action_repository] = lambda: ActionRepo([action])
    try:
        response = TestClient(app).post("/api/problems/problem-1/status", json={"to_status": "closed", "changed_by": "Rafael", "reason": "Readiness reviewed and accepted"})
        assert response.status_code == 200
        assert response.json()["status"] == "closed"
        assert response.json()["status_history"][0]["changed_by"] == "Rafael"
        assert repository.problem.status is ProblemStatus.CLOSED
    finally:
        app.dependency_overrides.clear()
