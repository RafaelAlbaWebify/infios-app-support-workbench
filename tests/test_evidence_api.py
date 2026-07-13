from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


def _client(tmp_path):
    database_path = tmp_path / "cases.sqlite3"
    case_repository = SQLiteCaseRepository(database_path)
    evidence_repository = SQLiteEvidenceRepository(database_path)
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/api/cases",
        json={
            "title": "Orders page fails after login",
            "application": "Order Management",
            "affected_scope": "Several users",
        },
    )
    assert response.status_code == 201
    return response.json()["case_id"]


def test_create_list_and_get_evidence_for_case(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        create_response = client.post(
            f"/api/cases/{case_id}/evidence",
            json={
                "evidence_type": "user_report",
                "source": "service desk",
                "content": "User can log in but Orders returns an error.",
                "certainty": "reported",
                "sensitivity": "internal",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["case_id"] == case_id
        assert created["evidence_id"].startswith("evidence-")
        assert created["certainty"] == "reported"

        list_response = client.get(f"/api/cases/{case_id}/evidence")
        assert list_response.status_code == 200
        listing = list_response.json()
        assert listing["count"] == 1
        assert listing["evidence"][0] == created

        get_response = client.get(
            f"/api/cases/{case_id}/evidence/{created['evidence_id']}"
        )
        assert get_response.status_code == 200
        assert get_response.json() == created
    finally:
        app.dependency_overrides.clear()


def test_evidence_requires_an_existing_case(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        response = client.post(
            "/api/cases/case-missing/evidence",
            json={
                "evidence_type": "error_message",
                "source": "user",
                "content": "Something went wrong",
            },
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Support case not found"}
    finally:
        app.dependency_overrides.clear()


def test_evidence_cannot_be_retrieved_through_another_case(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        first_case = _create_case(client)
        second_case = _create_case(client)
        created = client.post(
            f"/api/cases/{first_case}/evidence",
            json={
                "evidence_type": "http_observation",
                "source": "browser developer tools",
                "content": {"status": 500, "endpoint": "/api/orders"},
                "certainty": "technically_confirmed",
            },
        ).json()

        response = client.get(
            f"/api/cases/{second_case}/evidence/{created['evidence_id']}"
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Evidence item not found"}
    finally:
        app.dependency_overrides.clear()


def test_evidence_api_validates_required_fields_and_limits(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        missing_source = client.post(
            f"/api/cases/{case_id}/evidence",
            json={"evidence_type": "user_report", "content": "Failure"},
        )
        assert missing_source.status_code == 422

        invalid_limit = client.get(f"/api/cases/{case_id}/evidence?limit=0")
        assert invalid_limit.status_code == 422
    finally:
        app.dependency_overrides.clear()
