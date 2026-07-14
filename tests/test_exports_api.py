from fastapi.testclient import TestClient

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.api.escalations import get_escalation_repository
from app.api.evidence import get_evidence_repository
from app.api.explanations import get_explanation_repository
from app.api.observations import get_observation_repository
from app.api.recovery import get_recovery_repository
from app.main import app
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_escalation_repository import SQLiteEscalationRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_explanation_repository import SQLiteExplanationRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository
from app.persistence.sqlite_recovery_repository import SQLiteRecoveryRepository


def _client(tmp_path) -> TestClient:
    database_path = tmp_path / "cases.sqlite3"
    app.dependency_overrides[get_case_repository] = lambda: SQLiteCaseRepository(database_path)
    app.dependency_overrides[get_evidence_repository] = lambda: SQLiteEvidenceRepository(database_path)
    app.dependency_overrides[get_observation_repository] = lambda: SQLiteObservationRepository(database_path)
    app.dependency_overrides[get_action_repository] = lambda: SQLiteActionRepository(database_path)
    app.dependency_overrides[get_explanation_repository] = lambda: SQLiteExplanationRepository(database_path)
    app.dependency_overrides[get_escalation_repository] = lambda: SQLiteEscalationRepository(database_path)
    app.dependency_overrides[get_recovery_repository] = lambda: SQLiteRecoveryRepository(database_path)
    return TestClient(app)


def test_download_case_summary_as_markdown(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        support_case = client.post(
            "/api/cases",
            json={
                "title": "Orders fail after login",
                "application": "Order Management",
                "impact": "Order submission is blocked",
                "affected_scope": "Several users",
            },
        ).json()
        case_id = support_case["case_id"]
        evidence = client.post(
            f"/api/cases/{case_id}/evidence",
            json={
                "evidence_type": "http_observation",
                "source": "browser developer tools",
                "content": "POST /api/orders returned HTTP 500",
                "certainty": "technically_confirmed",
            },
        ).json()
        client.post(
            f"/api/cases/{case_id}/observations",
            json={
                "statement": "HTTP 500 was observed on /api/orders.",
                "category": "http",
                "evidence_ids": [evidence["evidence_id"]],
                "certainty": "technically_confirmed",
            },
        )

        response = client.get(f"/api/cases/{case_id}/summary/download")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/markdown")
        assert f'infios-{case_id}-summary.md' in response.headers["content-disposition"]
        assert "# Case summary: Orders fail after login" in response.text
        assert "## Evidence-backed observations" in response.text
        assert "HTTP 500 was observed on /api/orders." in response.text
        assert "no unconfirmed explanation is presented as root cause" in response.text
    finally:
        app.dependency_overrides.clear()


def test_download_persisted_escalation_as_markdown(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        support_case = client.post(
            "/api/cases",
            json={"title": "Orders fail", "application": "Order Management"},
        ).json()
        case_id = support_case["case_id"]
        package = client.post(
            f"/api/cases/{case_id}/escalations",
            json={
                "target_team": "L2 Application Support",
                "requested_action": "Review the application logs.",
            },
        ).json()

        response = client.get(
            f"/api/cases/{case_id}/escalations/{package['package_id']}/download"
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/markdown")
        assert package["package_id"] in response.headers["content-disposition"]
        assert response.text == package["report_text"]
    finally:
        app.dependency_overrides.clear()


def test_export_routes_reject_unknown_resources(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        assert client.get("/api/cases/case-missing/summary/download").status_code == 404
        support_case = client.post(
            "/api/cases",
            json={"title": "Sample", "application": "Sample App"},
        ).json()
        assert (
            client.get(
                f"/api/cases/{support_case['case_id']}/escalations/package-missing/download"
            ).status_code
            == 404
        )
    finally:
        app.dependency_overrides.clear()
