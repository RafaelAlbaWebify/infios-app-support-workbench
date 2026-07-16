from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.problem_actions import get_problem_action_repository
from app.api.problems import get_problem_repository
from app.main import app
from app.persistence.sqlite_problem_action_repository import SQLiteProblemActionRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_action_models import ProblemActionSafety, ProblemActionStatus, ProblemActionType, ProblemCorrectiveAction
from app.problem_models import ProblemRecord


def test_change_action_cannot_be_read_only() -> None:
    try:
        ProblemCorrectiveAction(
            problem_id="problem-1",
            title="Apply approved configuration change",
            description="Apply the approved configuration change.",
            action_type=ProblemActionType.CORRECTIVE,
            safety=ProblemActionSafety.READ_ONLY,
            owner="Platform Team",
            created_by="operator-1",
            requires_write_or_restart=True,
        )
    except ValueError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("Expected unsafe classification to fail")


def test_validated_action_requires_implementation_evidence() -> None:
    try:
        ProblemCorrectiveAction(
            problem_id="problem-1",
            title="Deploy fix",
            description="Deploy the approved fix.",
            action_type=ProblemActionType.CORRECTIVE,
            status=ProblemActionStatus.VALIDATED,
            safety=ProblemActionSafety.APPROVED_CHANGE_REQUIRED,
            owner="Application Team",
            created_by="operator-1",
            completed_by="operator-2",
            completed_at=datetime.now(timezone.utc),
        )
    except ValueError as exc:
        assert "implementation evidence" in str(exc)
    else:
        raise AssertionError("Expected completion validation to fail")


def test_problem_action_api_completion_gate(tmp_path) -> None:
    database = tmp_path / "workbench.sqlite3"
    problem_repository = SQLiteProblemRepository(database)
    action_repository = SQLiteProblemActionRepository(database)
    problem = problem_repository.save(
        ProblemRecord(
            title="Recurring login issue",
            summary="Recurring incidents under investigation.",
            owner="Application Support",
            created_by="operator-1",
            case_ids=["case-1"],
        )
    )

    app.dependency_overrides[get_problem_repository] = lambda: problem_repository
    app.dependency_overrides[get_problem_action_repository] = lambda: action_repository
    client = TestClient(app)

    try:
        created = client.post(
            f"/api/problems/{problem.problem_id}/actions",
            json={
                "title": "Deploy cache fix",
                "description": "Deploy the approved cache invalidation change.",
                "action_type": "corrective",
                "safety": "approved_change_required",
                "owner": "Application Team",
                "created_by": "operator-1",
                "due_date": "2026-08-01",
                "requires_write_or_restart": True,
            },
        )
        assert created.status_code == 201
        action_id = created.json()["action_id"]

        rejected = client.post(
            f"/api/problems/{problem.problem_id}/actions/{action_id}/status",
            json={"status": "implemented", "completed_by": "operator-2"},
        )
        assert rejected.status_code == 422

        validated = client.post(
            f"/api/problems/{problem.problem_id}/actions/{action_id}/status",
            json={
                "status": "validated",
                "implementation_evidence_reference": "change:CHG-1001/deployment-log",
                "validation_result": "No recurrence during the agreed observation window.",
                "completed_by": "operator-2",
            },
        )
        assert validated.status_code == 200
        assert validated.json()["status"] == "validated"

        listed = client.get(f"/api/problems/{problem.problem_id}/actions")
        assert listed.status_code == 200
        assert listed.json()["count"] == 1
    finally:
        app.dependency_overrides.clear()
