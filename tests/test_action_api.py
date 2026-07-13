from fastapi.testclient import TestClient

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.main import app
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def _client(tmp_path):
    database_path = tmp_path / "cases.sqlite3"
    case_repository = SQLiteCaseRepository(database_path)
    action_repository = SQLiteActionRepository(database_path)
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_action_repository] = lambda: action_repository
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/api/cases",
        json={"title": "Orders page fails after login", "application": "Order Management"},
    )
    assert response.status_code == 201
    return response.json()["case_id"]


def test_create_start_complete_and_retrieve_diagnostic_action(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        create_response = client.post(
            f"/api/cases/{case_id}/actions",
            json={
                "name": "Compare with another approved test user",
                "purpose": "Determine whether the symptom is user-specific.",
                "safety_level": "l1_safe",
                "expected_result": "Record whether the same feature fails.",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["status"] == "recommended"

        started = client.post(
            f"/api/cases/{case_id}/actions/{created['action_id']}/start"
        )
        assert started.status_code == 200
        assert started.json()["status"] == "in_progress"
        assert started.json()["started_at"] is not None

        completed = client.post(
            f"/api/cases/{case_id}/actions/{created['action_id']}/complete",
            json={
                "actual_result": "The same error reproduced with a second approved user.",
                "conclusion": "The issue is less likely to be isolated to one user.",
                "performed_by": "L1 Support",
            },
        )
        assert completed.status_code == 200
        result = completed.json()
        assert result["status"] == "completed"
        assert result["completed_at"] is not None
        assert result["actual_result"].startswith("The same error")

        listing = client.get(f"/api/cases/{case_id}/actions").json()
        assert listing["count"] == 1
        assert listing["actions"][0] == result

        retrieved = client.get(
            f"/api/cases/{case_id}/actions/{created['action_id']}"
        )
        assert retrieved.status_code == 200
        assert retrieved.json() == result
    finally:
        app.dependency_overrides.clear()


def test_write_or_restart_action_cannot_be_l1_safe(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        response = client.post(
            f"/api/cases/{case_id}/actions",
            json={
                "name": "Restart production service",
                "purpose": "Attempt recovery",
                "safety_level": "l1_safe",
                "requires_write_or_restart": True,
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_action_isolated_by_case_and_completion_requires_result(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        first_case = _create_case(client)
        second_case = _create_case(client)
        action = client.post(
            f"/api/cases/{first_case}/actions",
            json={
                "name": "Capture request boundary",
                "purpose": "Collect HTTP evidence",
                "safety_level": "l1_safe",
            },
        ).json()

        cross_case = client.get(
            f"/api/cases/{second_case}/actions/{action['action_id']}"
        )
        assert cross_case.status_code == 404

        missing_result = client.post(
            f"/api/cases/{first_case}/actions/{action['action_id']}/complete",
            json={"actual_result": ""},
        )
        assert missing_result.status_code == 422
    finally:
        app.dependency_overrides.clear()
