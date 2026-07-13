from fastapi.testclient import TestClient

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.api.escalations import get_escalation_repository
from app.api.evidence import get_evidence_repository
from app.api.explanations import get_explanation_repository
from app.api.observations import get_observation_repository
from app.main import app
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_escalation_repository import SQLiteEscalationRepository
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
    app.dependency_overrides[get_escalation_repository] = lambda: SQLiteEscalationRepository(database_path)
    return TestClient(app)


def test_generate_persist_and_retrieve_l2_escalation(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case = client.post(
            "/api/cases",
            json={
                "title": "Orders page fails after login",
                "application": "Order Management",
                "impact": "Order submission is blocked",
                "affected_scope": "Three users",
            },
        ).json()
        case_id = case["case_id"]
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
        ).json()
        explanation = client.post(
            f"/api/cases/{case_id}/explanations",
            json={
                "statement": "The Orders endpoint is failing in the application layer.",
                "supporting_observation_ids": [observation["observation_id"]],
            },
        )
        assert explanation.status_code == 201

        created = client.post(
            f"/api/cases/{case_id}/escalations",
            json={
                "target_team": "L2 Application Support",
                "requested_action": "Review application logs for the failing endpoint and timestamp.",
            },
        )
        assert created.status_code == 201
        package = created.json()
        assert evidence["evidence_id"] in package["included_evidence_ids"]
        assert "## Confirmed observations" in package["report_text"]
        assert "## Possible explanations — unconfirmed" in package["report_text"]
        assert "HTTP 500 was observed on /api/orders." in package["report_text"]
        assert "does not treat temporal correlation" in package["report_text"]

        listing = client.get(f"/api/cases/{case_id}/escalations")
        assert listing.status_code == 200
        assert listing.json()["count"] == 1

        retrieved = client.get(
            f"/api/cases/{case_id}/escalations/{package['package_id']}"
        )
        assert retrieved.status_code == 200
        assert retrieved.json() == package
    finally:
        app.dependency_overrides.clear()


def test_escalation_exposes_missing_information(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case = client.post(
            "/api/cases",
            json={"title": "Unknown failure", "application": "Sample App"},
        ).json()
        response = client.post(
            f"/api/cases/{case['case_id']}/escalations",
            json={"target_team": "L2", "requested_action": "Investigate the incident."},
        )
        assert response.status_code == 201
        missing = response.json()["missing_information"]
        assert "Business impact is unknown." in missing
        assert "Affected scope is unknown." in missing
        assert "No evidence has been captured." in missing
    finally:
        app.dependency_overrides.clear()
