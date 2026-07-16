from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.problem_actions import get_problem_action_repository
from app.api.problem_rca import get_problem_rca_repository
from app.api.problems import get_problem_repository
from app.main import app
from app.persistence.sqlite_problem_action_repository import SQLiteProblemActionRepository
from app.persistence.sqlite_problem_rca_repository import SQLiteProblemRCARepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_action_models import ProblemActionSafety, ProblemActionStatus, ProblemActionType, ProblemCorrectiveAction
from app.problem_models import ProblemRecord
from app.problem_rca_models import ProblemRCAStatement, RCAStatus
from app.problem_readiness import build_problem_closure_readiness


def _confirmed_rca(problem_id: str) -> ProblemRCAStatement:
    return ProblemRCAStatement(
        problem_id=problem_id,
        statement="Confirmed shared cause.",
        status=RCAStatus.CONFIRMED,
        supporting_explanation_ids=["explanation-1"],
        created_by="operator-1",
        confirmed_by="operator-2",
        confirmation_reason="Evidence-backed case explanation reviewed.",
        confirmed_at=datetime.now(timezone.utc),
    )


def _validated_action(problem_id: str) -> ProblemCorrectiveAction:
    return ProblemCorrectiveAction(
        problem_id=problem_id,
        title="Deploy corrective change",
        description="Apply and validate the approved change.",
        action_type=ProblemActionType.CORRECTIVE,
        status=ProblemActionStatus.VALIDATED,
        safety=ProblemActionSafety.APPROVED_CHANGE_REQUIRED,
        owner="Application Team",
        created_by="operator-1",
        implementation_evidence_reference="change:CHG-1001/deployment-log",
        validation_result="No recurrence during the agreed observation window.",
        completed_by="operator-2",
        completed_at=datetime.now(timezone.utc),
    )


def test_readiness_requires_confirmed_rca_and_validated_actions() -> None:
    report = build_problem_closure_readiness(
        problem_id="problem-1",
        rca_statements=[],
        actions=[
            ProblemCorrectiveAction(
                problem_id="problem-1",
                title="Add monitoring",
                description="Add monitoring coverage.",
                action_type=ProblemActionType.MONITORING,
                safety=ProblemActionSafety.READ_ONLY,
                owner="Operations",
                created_by="operator-1",
                due_date=date(2026, 1, 1),
            )
        ],
        today=date(2026, 7, 16),
    )
    assert report.status == "not_ready"
    assert report.blockers == ["no_confirmed_rca", "actions_not_validated", "overdue_actions"]


def test_readiness_is_advisory_when_all_prerequisites_exist() -> None:
    report = build_problem_closure_readiness(
        problem_id="problem-1",
        rca_statements=[_confirmed_rca("problem-1")],
        actions=[_validated_action("problem-1")],
        today=date(2026, 7, 16),
    )
    assert report.status == "ready"
    assert report.ready_for_operator_review is True
    assert report.blockers == []


def test_problem_readiness_api_aggregates_persisted_records(tmp_path) -> None:
    database = tmp_path / "workbench.sqlite3"
    problem_repository = SQLiteProblemRepository(database)
    rca_repository = SQLiteProblemRCARepository(database)
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
    rca_repository.save(_confirmed_rca(problem.problem_id))
    action_repository.save(_validated_action(problem.problem_id))

    app.dependency_overrides[get_problem_repository] = lambda: problem_repository
    app.dependency_overrides[get_problem_rca_repository] = lambda: rca_repository
    app.dependency_overrides[get_problem_action_repository] = lambda: action_repository
    client = TestClient(app)

    try:
        response = client.get(f"/api/problems/{problem.problem_id}/closure-readiness")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
        assert response.json()["confirmed_rca_count"] == 1
        assert response.json()["validated_action_count"] == 1
    finally:
        app.dependency_overrides.clear()
