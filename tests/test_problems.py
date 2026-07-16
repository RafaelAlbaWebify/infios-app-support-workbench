from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.problems import get_problem_repository
from app.domain.models import SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_models import ProblemRecord, ProblemStatus


def test_problem_record_rejects_duplicate_case_ids() -> None:
    try:
        ProblemRecord(
            title="Recurring login failure",
            summary="Repeated login failures across two incident windows.",
            owner="Application Support",
            created_by="operator-1",
            case_ids=["case-1", "case-1"],
        )
    except ValueError as exc:
        assert "cannot be linked" in str(exc)
    else:
        raise AssertionError("Expected duplicate case validation to fail")


def test_problem_repository_lists_active_records_by_default(tmp_path) -> None:
    repository = SQLiteProblemRepository(tmp_path / "problems.sqlite3")
    active = repository.save(
        ProblemRecord(
            title="Queue delays",
            summary="Repeated processing delay incidents.",
            owner="Platform Support",
            created_by="operator-1",
            case_ids=["case-1", "case-2"],
        )
    )
    repository.save(
        ProblemRecord(
            title="Resolved timeout",
            summary="Historical timeout pattern.",
            status=ProblemStatus.RESOLVED,
            owner="Application Support",
            created_by="operator-2",
            case_ids=["case-3"],
        )
    )

    assert repository.get(active.problem_id) == active
    assert repository.list() == [active]
    assert len(repository.list(active_only=False)) == 2


def test_problem_api_validates_cases_and_returns_occurrence_count(tmp_path) -> None:
    case_repository = SQLiteCaseRepository(tmp_path / "workbench.sqlite3")
    problem_repository = SQLiteProblemRepository(tmp_path / "workbench.sqlite3")
    first = case_repository.save(SupportCase(title="Login incident one", application="Portal"))
    second = case_repository.save(SupportCase(title="Login incident two", application="Portal"))

    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_problem_repository] = lambda: problem_repository
    client = TestClient(app)

    try:
        response = client.post(
            "/api/problems",
            json={
                "title": "Recurring portal login failure",
                "summary": "Two separate cases show the same user-visible failure pattern.",
                "owner": "Application Support",
                "created_by": "operator-1",
                "case_ids": [first.case_id, second.case_id],
                "recurrence_notes": "Occurrences are related by operator review, not automatic matching.",
            },
        )
        assert response.status_code == 201
        assert response.json()["occurrence_count"] == 2

        listed = client.get("/api/problems")
        assert listed.status_code == 200
        assert listed.json()["count"] == 1

        missing_case = client.post(
            "/api/problems",
            json={
                "title": "Invalid problem",
                "summary": "References a missing case.",
                "owner": "Application Support",
                "created_by": "operator-1",
                "case_ids": ["case-missing"],
            },
        )
        assert missing_case.status_code == 422
        assert missing_case.json()["detail"]["invalid_case_ids"] == ["case-missing"]
    finally:
        app.dependency_overrides.clear()
