from fastapi.testclient import TestClient

from app.main import app


def test_guided_workbench_is_served_at_root() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "INFIOS" in response.text
    assert "Safe guided checks" in response.text
    assert "Review and escalate" in response.text
    assert "Generate L2 handover" in response.text
    assert "Case lifecycle and recovery" in response.text
    assert "Save recovery validation" in response.text


def test_guided_workbench_assets_are_served() -> None:
    client = TestClient(app)
    stylesheet = client.get("/ui/static/styles.css")
    script = client.get("/ui/static/app.js")
    guided_script = client.get("/ui/static/guided.js")
    escalation_script = client.get("/ui/static/escalation.js")
    lifecycle_script = client.get("/ui/static/lifecycle.js")

    assert stylesheet.status_code == 200
    assert ".case-card" in stylesheet.text
    assert script.status_code == 200
    assert "/api/cases?limit=20" in script.text
    assert guided_script.status_code == 200
    assert "requires_write_or_restart: false" in guided_script.text
    assert escalation_script.status_code == 200
    assert "/escalations" in escalation_script.text
    assert "target_team" in escalation_script.text
    assert lifecycle_script.status_code == 200
    assert "/status" in lifecycle_script.text
    assert "/recovery-validations" in lifecycle_script.text
    assert "Passed recovery validation requires supporting evidence" in lifecycle_script.text


def test_case_api_contract_supports_dashboard_and_resume() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/cases",
        json={"title": "Orders page fails", "application": "Order Management"},
    )
    assert created.status_code == 201
    case_id = created.json()["case_id"]
    assert any(
        item["case_id"] == case_id
        for item in client.get("/api/cases?limit=20").json()["cases"]
    )
    assert client.get(f"/api/cases/{case_id}").status_code == 200
    assert client.get(f"/api/cases/{case_id}/summary").status_code == 200


def test_guided_check_api_contract_supports_recording_a_safe_result() -> None:
    client = TestClient(app)
    support_case = client.post(
        "/api/cases",
        json={"title": "Orders page fails after login", "application": "Order Management"},
    ).json()
    case_id = support_case["case_id"]
    check = client.get(
        f"/api/cases/{case_id}/playbooks/post-login-feature-failure"
    ).json()["recommended_checks"][0]
    created = client.post(
        f"/api/cases/{case_id}/actions",
        json={
            "name": check["name"],
            "purpose": check["purpose"],
            "safety_level": check["safety_level"],
            "requires_write_or_restart": False,
        },
    ).json()
    action_id = created["action_id"]
    assert client.post(f"/api/cases/{case_id}/actions/{action_id}/start").status_code == 200
    completed = client.post(
        f"/api/cases/{case_id}/actions/{action_id}/complete",
        json={"actual_result": "Login succeeds and the Orders page fails."},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_escalation_api_contract_generates_persistent_l2_handover() -> None:
    client = TestClient(app)
    support_case = client.post(
        "/api/cases",
        json={
            "title": "Orders page fails after login",
            "application": "Order Management",
            "affected_scope": "several users",
            "impact": "important function unavailable",
        },
    ).json()
    case_id = support_case["case_id"]
    client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "evidence_type": "error_message",
            "source": "browser",
            "content": "HTTP 500 after login",
            "certainty": "technically_confirmed",
        },
    )

    created = client.post(
        f"/api/cases/{case_id}/escalations",
        json={
            "target_team": "L2 Application Support",
            "requested_action": "Review application logs for the failing request.",
        },
    )
    listed = client.get(f"/api/cases/{case_id}/escalations")

    assert created.status_code == 201
    assert created.json()["target_team"] == "L2 Application Support"
    assert "## Requested support" in created.json()["report_text"]
    assert listed.status_code == 200
    assert listed.json()["count"] == 1


def test_lifecycle_and_recovery_api_contract_requires_evidence_for_passed_result() -> None:
    client = TestClient(app)
    support_case = client.post(
        "/api/cases",
        json={"title": "Orders page fails", "application": "Order Management"},
    ).json()
    case_id = support_case["case_id"]

    assert client.post(
        f"/api/cases/{case_id}/status", json={"status": "information_gathering"}
    ).status_code == 200
    assert client.post(
        f"/api/cases/{case_id}/status", json={"status": "investigation"}
    ).status_code == 200
    assert client.post(
        f"/api/cases/{case_id}/status", json={"status": "recovery_validation"}
    ).status_code == 200

    without_evidence = client.post(
        f"/api/cases/{case_id}/recovery-validations",
        json={
            "outcome": "passed",
            "method": "Repeat the affected operation",
            "result": "Orders page opened successfully",
            "performed_by": "L1 Support",
        },
    )
    assert without_evidence.status_code == 422

    evidence = client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "evidence_type": "recovery_result",
            "source": "affected user and L1 Support",
            "content": "Orders page opened successfully twice",
            "certainty": "reproduced",
        },
    ).json()
    validation = client.post(
        f"/api/cases/{case_id}/recovery-validations",
        json={
            "outcome": "passed",
            "method": "Repeat the affected operation",
            "result": "Orders page opened successfully twice",
            "performed_by": "L1 Support",
            "evidence_ids": [evidence["evidence_id"]],
        },
    )
    assert validation.status_code == 201
    assert validation.json()["outcome"] == "passed"
    assert client.get(f"/api/cases/{case_id}/recovery-validations").json()["count"] == 1


def test_api_documentation_remains_available() -> None:
    response = TestClient(app).get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text
