from datetime import date

from fastapi.testclient import TestClient

from app.api.problem_actions import get_problem_action_repository
from app.api.problems import get_problem_repository
from app.main import app
from app.persistence.sqlite_problem_action_repository import SQLiteProblemActionRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_action_models import (
    ProblemActionSafety,
    ProblemActionStatus,
    ProblemActionType,
    ProblemCorrectiveAction,
)
from app.problem_action_workload import build_problem_action_workload_report
from app.problem_models import ProblemRecord


def _action(**overrides) -> ProblemCorrectiveAction:
    data = {
        "problem_id": "problem-1",
        "title": "Update monitoring",
        "description": "Add a targeted alert.",
        "action_type": ProblemActionType.MONITORING,
        "safety": ProblemActionSafety.READ_ONLY,
        "owner": "Application Support",
        "created_by": "operator-1",
    }
    data.update(overrides)
    return ProblemCorrectiveAction(**data)


def test_workload_report_identifies_attention_conditions() -> None:
    actions = [
        _action(due_date=date(2026, 7, 10)),
        _action(title="Blocked change", status=ProblemActionStatus.BLOCKED),
        _action(
            title="Awaiting validation",
            status=ProblemActionStatus.IMPLEMENTED,
            safety=ProblemActionSafety.APPROVED_CHANGE_REQUIRED,
            implementation_evidence_reference="change-123",
            completed_by="operator-2",
            completed_at="2026-07-15T10:00:00Z",
        ),
        _action(title="Cancelled item", status=ProblemActionStatus.CANCELLED),
    ]

    report = build_problem_action_workload_report(actions, today=date(2026, 7, 16))

    assert report.total_action_count == 4
    assert report.active_action_count == 3
    assert report.overdue_action_count == 1
    assert report.blocked_action_count == 1
    assert report.validation_pending_count == 1
    assert len(report.attention_items) == 3
    assert report.attention_items[0].overdue is True


def test_problem_action_workload_api_aggregates_all_problems(tmp_path) -> None:
    database = tmp_path / "workbench.sqlite3"
    problem_repository = SQLiteProblemRepository(database)
    action_repository = SQLiteProblemActionRepository(database)
    problem = problem_repository.save(
        ProblemRecord(
            title="Recurring issue",
            summary="Operator-defined recurrence.",
            owner="Application Support",
            created_by="operator-1",
            case_ids=["case-1"],
        )
    )
    action_repository.save(_action(problem_id=problem.problem_id, status=ProblemActionStatus.BLOCKED))

    app.dependency_overrides[get_problem_repository] = lambda: problem_repository
    app.dependency_overrides[get_problem_action_repository] = lambda: action_repository
    client = TestClient(app)

    try:
        response = client.get("/api/analytics/problem-action-workload")
        assert response.status_code == 200
        payload = response.json()
        assert payload["total_action_count"] == 1
        assert payload["blocked_action_count"] == 1
        assert payload["actions_by_owner"] == {"Application Support": 1}
        assert "performance" in payload["disclaimer"]
    finally:
        app.dependency_overrides.clear()
