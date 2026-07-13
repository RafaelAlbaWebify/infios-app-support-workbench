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


def test_playbook_guides_post_login_failure_without_claiming_root_cause(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case = client.post(
            "/api/cases",
            json={
                "title": "Orders page fails after login",
                "application": "Order Management",
                "impact": "Order submission is blocked",
                "affected_scope": "Several users",
            },
        ).json()
        case_id = case["case_id"]
        report = client.post(
            f"/api/cases/{case_id}/evidence",
            json={
                "evidence_type": "user_report",
                "source": "service desk",
                "content": "Users can log in but the Orders page returns an error.",
                "certainty": "reported",
            },
        ).json()
        http = client.post(
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
                "evidence_ids": [http["evidence_id"]],
                "certainty": "technically_confirmed",
            },
        ).json()

        response = client.get(
            f"/api/cases/{case_id}/playbooks/post-login-feature-failure"
        )
        assert response.status_code == 200
        result = response.json()
        assert result["applicable"] is True
        assert observation["observation_id"] in result["confirmed_observation_ids"]
        assert any(item["safety_level"] == "l1_safe" for item in result["recommended_checks"])
        assert "Recent deployment, configuration, or permission-change context" in result["missing_evidence"]
        assert all("root cause is" not in text.lower() for text in result["possible_explanations"])
        assert any("not proof of root cause" in warning for warning in result["safety_warnings"])
        assert report["evidence_id"] not in result["confirmed_observation_ids"]
    finally:
        app.dependency_overrides.clear()


def test_playbook_is_not_applicable_without_post_login_evidence(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        case_id = client.post(
            "/api/cases",
            json={"title": "Application unavailable", "application": "Order Management"},
        ).json()["case_id"]
        response = client.get(
            f"/api/cases/{case_id}/playbooks/post-login-feature-failure"
        )
        assert response.status_code == 200
        result = response.json()
        assert result["applicable"] is False
        assert len(result["recommended_checks"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_playbook_returns_not_found_for_unknown_case(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        response = client.get(
            "/api/cases/case-missing/playbooks/post-login-feature-failure"
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Support case not found"}
    finally:
        app.dependency_overrides.clear()
