from fastapi.testclient import TestClient

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.explanations import get_explanation_repository
from app.api.observations import get_observation_repository
from app.main import app
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_explanation_repository import SQLiteExplanationRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository


def _client(tmp_path):
    database_path = tmp_path / "cases.sqlite3"
    app.dependency_overrides[get_case_repository] = lambda: SQLiteCaseRepository(database_path)
    app.dependency_overrides[get_evidence_repository] = lambda: SQLiteEvidenceRepository(database_path)
    app.dependency_overrides[get_observation_repository] = lambda: SQLiteObservationRepository(database_path)
    app.dependency_overrides[get_action_repository] = lambda: SQLiteActionRepository(database_path)
    app.dependency_overrides[get_explanation_repository] = lambda: SQLiteExplanationRepository(database_path)
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/api/cases",
        json={"title": "Orders page fails", "application": "Order Management"},
    )
    assert response.status_code == 201
    return response.json()["case_id"]


def _create_observation(client: TestClient, case_id: str) -> str:
    evidence = client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "evidence_type": "http_observation",
            "source": "browser developer tools",
            "content": {"status": 500, "endpoint": "/api/orders"},
            "certainty": "technically_confirmed",
        },
    ).json()
    observation = client.post(
        f"/api/cases/{case_id}/observations",
        json={
            "statement": "HTTP 500 was observed on /api/orders.",
            "category": "http",
            "evidence_ids": [evidence["evidence_id"]],
            "certainty": "technically_confirmed",
        },
    )
    assert observation.status_code == 201
    return observation.json()["observation_id"]


def test_create_list_and_confirm_supported_explanation(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        observation_id = _create_observation(client, case_id)
        created = client.post(
            f"/api/cases/{case_id}/explanations",
            json={
                "statement": "The Orders endpoint is failing in the application layer.",
                "supporting_observation_ids": [observation_id],
            },
        )
        assert created.status_code == 201
        explanation = created.json()
        assert explanation["status"] == "proposed"

        confirmed = client.post(
            f"/api/cases/{case_id}/explanations/{explanation['explanation_id']}/status",
            json={"status": "confirmed", "confirmed_by_operator": True},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"

        listing = client.get(f"/api/cases/{case_id}/explanations")
        assert listing.status_code == 200
        assert listing.json()["count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_confirmation_requires_support_and_operator_confirmation(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = _create_case(client)
        explanation = client.post(
            f"/api/cases/{case_id}/explanations",
            json={"statement": "A database issue caused the failure."},
        ).json()

        no_support = client.post(
            f"/api/cases/{case_id}/explanations/{explanation['explanation_id']}/status",
            json={"status": "confirmed", "confirmed_by_operator": True},
        )
        assert no_support.status_code == 422

        no_operator = client.post(
            f"/api/cases/{case_id}/explanations/{explanation['explanation_id']}/status",
            json={"status": "confirmed", "confirmed_by_operator": False},
        )
        assert no_operator.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_cross_case_observation_reference_is_rejected(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        first_case = _create_case(client)
        second_case = _create_case(client)
        observation_id = _create_observation(client, first_case)

        response = client.post(
            f"/api/cases/{second_case}/explanations",
            json={
                "statement": "The endpoint failed.",
                "supporting_observation_ids": [observation_id],
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"] == {"invalid_observation_ids": [observation_id]}
    finally:
        app.dependency_overrides.clear()
