from fastapi.testclient import TestClient

from app.api.explanations import get_explanation_repository
from app.api.problem_rca import get_problem_rca_repository
from app.api.problems import get_problem_repository
from app.domain.models import ExplanationStatus, PossibleExplanation
from app.main import app
from app.persistence.sqlite_explanation_repository import SQLiteExplanationRepository
from app.persistence.sqlite_problem_rca_repository import SQLiteProblemRCARepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_models import ProblemRecord


def test_confirmed_problem_rca_requires_operator_confirmation() -> None:
    try:
        from app.problem_rca_models import ProblemRCAStatement, RCAStatus

        ProblemRCAStatement(
            problem_id="problem-1",
            statement="Shared cause",
            status=RCAStatus.CONFIRMED,
            supporting_explanation_ids=["explanation-1"],
            created_by="operator-1",
        )
    except ValueError as exc:
        assert "operator identity" in str(exc)
    else:
        raise AssertionError("Expected confirmed RCA validation to fail")


def test_problem_rca_api_requires_confirmed_case_explanations(tmp_path) -> None:
    database = tmp_path / "workbench.sqlite3"
    problem_repository = SQLiteProblemRepository(database)
    explanation_repository = SQLiteExplanationRepository(database)
    rca_repository = SQLiteProblemRCARepository(database)

    problem = problem_repository.save(
        ProblemRecord(
            title="Recurring login issue",
            summary="Two incidents grouped by operator review.",
            owner="Application Support",
            created_by="operator-1",
            case_ids=["case-1", "case-2"],
        )
    )
    proposed = explanation_repository.save(
        PossibleExplanation(
            case_id="case-1",
            statement="Identity cache entries are stale.",
            supporting_observation_ids=["observation-1"],
        )
    )

    app.dependency_overrides[get_problem_repository] = lambda: problem_repository
    app.dependency_overrides[get_explanation_repository] = lambda: explanation_repository
    app.dependency_overrides[get_problem_rca_repository] = lambda: rca_repository
    client = TestClient(app)

    try:
        created = client.post(
            f"/api/problems/{problem.problem_id}/rca",
            json={
                "statement": "Stale identity cache entries caused the recurring failures.",
                "supporting_explanation_ids": [proposed.explanation_id],
                "created_by": "operator-1",
            },
        )
        assert created.status_code == 201
        rca_id = created.json()["rca_id"]

        rejected = client.post(
            f"/api/problems/{problem.problem_id}/rca/{rca_id}/confirm",
            json={"confirmed_by": "operator-2", "confirmation_reason": "Reviewed evidence."},
        )
        assert rejected.status_code == 422

        explanation_repository.save(
            PossibleExplanation.model_validate(
                {
                    **proposed.model_dump(),
                    "status": ExplanationStatus.CONFIRMED,
                    "confirmed_by_operator": True,
                }
            )
        )
        confirmed = client.post(
            f"/api/problems/{problem.problem_id}/rca/{rca_id}/confirm",
            json={
                "confirmed_by": "operator-2",
                "confirmation_reason": "Confirmed case explanation is evidence-backed and applicable to the problem.",
            },
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"
        assert confirmed.json()["confirmed_by"] == "operator-2"
    finally:
        app.dependency_overrides.clear()
