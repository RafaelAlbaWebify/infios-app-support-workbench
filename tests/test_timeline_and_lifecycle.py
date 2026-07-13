from fastapi.testclient import TestClient

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.observations import get_observation_repository
from app.main import app
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository


def _client(tmp_path):
    database_path = tmp_path / "cases.sqlite3"
    case_repository = SQLiteCaseRepository(database_path)
    evidence_repository = SQLiteEvidenceRepository(database_path)
    observation_repository = SQLiteObservationRepository(database_path)
    action_repository = SQLiteActionRepository(database_path)
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    app.dependency_overrides[get_observation_repository] = lambda: observation_repository
    app.dependency_overrides[get_action_repository] = lambda: action_repository
    return TestClient(app)


def test_case_lifecycle_and_timeline_projection(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case = client.post(
            "/api/cases",
            json={"title": "Orders page fails", "application": "Order Management"},
        ).json()
        case_id = case["case_id"]

        transition = client.post(
            f"/api/cases/{case_id}/status",
            json={"status": "information_gathering"},
        )
        assert transition.status_code == 200
        assert transition.json()["status"] == "information_gathering"

        invalid = client.post(
            f"/api/cases/{case_id}/status",
            json={"status": "resolved"},
        )
        assert invalid.status_code == 409

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

        action = client.post(
            f"/api/cases/{case_id}/actions",
            json={
                "name": "Compare with another approved test user",
                "purpose": "Determine whether the issue is user-specific",
                "safety_level": "l1_safe",
            },
        ).json()
        assert client.post(f"/api/cases/{case_id}/actions/{action['action_id']}/start").status_code == 200
        assert client.post(
            f"/api/cases/{case_id}/actions/{action['action_id']}/complete",
            json={"actual_result": "The same error reproduced.", "performed_by": "L1 Support"},
        ).status_code == 200

        timeline = client.get(f"/api/cases/{case_id}/timeline")
        assert timeline.status_code == 200
        event_types = [event["event_type"] for event in timeline.json()["events"]]
        assert "case_created" in event_types
        assert "evidence" in event_types
        assert "observation" in event_types
        assert "action_started" in event_types
        assert "action_completed" in event_types
    finally:
        app.dependency_overrides.clear()
