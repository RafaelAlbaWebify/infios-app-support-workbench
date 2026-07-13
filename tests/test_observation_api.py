from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.observations import get_observation_repository
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository


def _client(tmp_path):
    database_path = tmp_path / "cases.sqlite3"
    case_repository = SQLiteCaseRepository(database_path)
    evidence_repository = SQLiteEvidenceRepository(database_path)
    observation_repository = SQLiteObservationRepository(database_path)
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    app.dependency_overrides[get_observation_repository] = lambda: observation_repository
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/api/cases",
        json={
            "title": "Orders page fails after login",
            "application": "Order Management",
        },
    )
    assert response.status_code == 201
    return response.json()["case_id"]


def _create_evidence(client: TestClient, case_id: str) -> str:
    response = client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "evidence_type": "http_observation",
            "source": "browser developer tools",
            "content": {"status": 500, "endpoint": "/api/orders"},
            "certainty": "technically_confirmed",
        },
    )
    assert response.status_code == 201
    return response.json()["evidence_id"]


def test_create_list_and_get_observation(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        evidence_id = _create_evidence(client, case_id)

        create_response = client.post(
            f"/api/cases/{case_id}/observations",
            json={
                "statement": "HTTP 500 was observed on /api/orders.",
                "category": "http",
                "evidence_ids": [evidence_id],
                "certainty": "technically_confirmed",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["case_id"] == case_id
        assert created["evidence_ids"] == [evidence_id]
        assert created["observation_id"].startswith("observation-")

        list_response = client.get(f"/api/cases/{case_id}/observations")
        assert list_response.status_code == 200
        listing = list_response.json()
        assert listing["count"] == 1
        assert listing["observations"][0] == created

        get_response = client.get(
            f"/api/cases/{case_id}/observations/{created['observation_id']}"
        )
        assert get_response.status_code == 200
        assert get_response.json() == created
    finally:
        app.dependency_overrides.clear()


def test_observation_rejects_missing_evidence(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        response = client.post(
            f"/api/cases/{case_id}/observations",
            json={
                "statement": "An error was observed.",
                "category": "application",
                "evidence_ids": ["evidence-missing"],
                "certainty": "reported",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"]["invalid_evidence_ids"] == [
            "evidence-missing"
        ]
    finally:
        app.dependency_overrides.clear()


def test_observation_rejects_evidence_from_another_case(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        first_case = _create_case(client)
        second_case = _create_case(client)
        evidence_id = _create_evidence(client, first_case)

        response = client.post(
            f"/api/cases/{second_case}/observations",
            json={
                "statement": "HTTP 500 was observed.",
                "category": "http",
                "evidence_ids": [evidence_id],
                "certainty": "technically_confirmed",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"]["invalid_evidence_ids"] == [evidence_id]
    finally:
        app.dependency_overrides.clear()


def test_observation_deduplicates_evidence_references(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        evidence_id = _create_evidence(client, case_id)
        response = client.post(
            f"/api/cases/{case_id}/observations",
            json={
                "statement": "HTTP 500 was observed.",
                "category": "http",
                "evidence_ids": [evidence_id, evidence_id],
                "certainty": "technically_confirmed",
            },
        )
        assert response.status_code == 201
        assert response.json()["evidence_ids"] == [evidence_id]
    finally:
        app.dependency_overrides.clear()


def test_observation_requires_existing_case_and_valid_limit(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        missing_case = client.get("/api/cases/case-missing/observations")
        assert missing_case.status_code == 404

        case_id = _create_case(client)
        invalid_limit = client.get(f"/api/cases/{case_id}/observations?limit=0")
        assert invalid_limit.status_code == 422
    finally:
        app.dependency_overrides.clear()
