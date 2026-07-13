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


def _client(tmp_path):
    database_path = tmp_path / "cases.sqlite3"
    app.dependency_overrides[get_case_repository] = lambda: SQLiteCaseRepository(database_path)
    app.dependency_overrides[get_evidence_repository] = lambda: SQLiteEvidenceRepository(database_path)
    app.dependency_overrides[get_observation_repository] = lambda: SQLiteObservationRepository(database_path)
    app.dependency_overrides[get_action_repository] = lambda: SQLiteActionRepository(database_path)
    app.dependency_overrides[get_explanation_repository] = lambda: SQLiteExplanationRepository(database_path)
    app.dependency_overrides[get_escalation_repository] = lambda: SQLiteEscalationRepository(database_path)
    app.dependency_overrides[get_recovery_repository] = lambda: SQLiteRecoveryRepository(database_path)
    return TestClient(app)


def test_passed_recovery_requires_same_case_evidence_and_appears_in_summary(tmp_path) -> None:
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
                "evidence_type": "reproduction_result",
                "source": "L1 validation",
                "content": "Order submission succeeded after recovery.",
                "certainty": "reproduced",
            },
        ).json()

        without_evidence = client.post(
            f"/api/cases/{case_id}/recovery-validations",
            json={
                "outcome": "passed",
                "method": "Repeat order submission",
                "result": "Order submitted successfully",
                "performed_by": "L1 Support",
            },
        )
        assert without_evidence.status_code == 422

        created = client.post(
            f"/api/cases/{case_id}/recovery-validations",
            json={
                "outcome": "passed",
                "method": "Repeat order submission",
                "result": "Order submitted successfully",
                "performed_by": "L1 Support",
                "evidence_ids": [evidence["evidence_id"]],
            },
        )
        assert created.status_code == 201
        validation = created.json()
        assert validation["outcome"] == "passed"

        summary = client.get(f"/api/cases/{case_id}/summary")
        assert summary.status_code == 200
        payload = summary.json()
        assert payload["case"]["case_id"] == case_id
        assert payload["recovery_validations"][0]["validation_id"] == validation["validation_id"]
        assert payload["playbook"]["playbook_id"] == "post-login-feature-failure"
        assert any(item["name"] == "Evidence" for item in payload["escalation_readiness"])
    finally:
        app.dependency_overrides.clear()


def test_recovery_rejects_cross_case_evidence(tmp_path) -> None:
    client = _client(tmp_path)
    try:
        first = client.post(
            "/api/cases", json={"title": "First", "application": "App"}
        ).json()
        second = client.post(
            "/api/cases", json={"title": "Second", "application": "App"}
        ).json()
        evidence = client.post(
            f"/api/cases/{first['case_id']}/evidence",
            json={
                "evidence_type": "reproduction_result",
                "source": "L1",
                "content": "Recovered",
            },
        ).json()

        response = client.post(
            f"/api/cases/{second['case_id']}/recovery-validations",
            json={
                "outcome": "passed",
                "method": "Retest",
                "result": "Passed",
                "performed_by": "L1",
                "evidence_ids": [evidence["evidence_id"]],
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"] == {
            "invalid_evidence_ids": [evidence["evidence_id"]]
        }
    finally:
        app.dependency_overrides.clear()
