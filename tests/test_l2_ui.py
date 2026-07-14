from fastapi.testclient import TestClient

from app.main import app


def test_l2_investigation_ui_and_asset_are_served() -> None:
    client = TestClient(app)
    page = client.get("/")
    script = client.get("/ui/static/l2.js")

    assert page.status_code == 200
    assert "Guided L1 + L2 mode" in page.text
    assert "Possible explanations" in page.text
    assert "Supporting observations" in page.text
    assert "Contradicting observations" in page.text
    assert script.status_code == 200
    assert "/explanations" in script.text
    assert "confirmed_by_operator" in script.text
    assert "deliberately reviewed the evidence" in script.text


def test_l2_explanation_contract_requires_support_before_confirmation() -> None:
    client = TestClient(app)
    support_case = client.post(
        "/api/cases",
        json={"title": "Orders page fails after login", "application": "Order Management"},
    ).json()
    case_id = support_case["case_id"]

    unsupported = client.post(
        f"/api/cases/{case_id}/explanations",
        json={"statement": "The application service may be failing after authentication."},
    )
    assert unsupported.status_code == 201
    unsupported_id = unsupported.json()["explanation_id"]
    rejected = client.post(
        f"/api/cases/{case_id}/explanations/{unsupported_id}/status",
        json={"status": "confirmed", "confirmed_by_operator": True},
    )
    assert rejected.status_code == 422

    evidence = client.post(
        f"/api/cases/{case_id}/evidence",
        json={
            "evidence_type": "http_observation",
            "source": "browser developer tools",
            "content": "POST /api/orders returned HTTP 500 after login",
            "certainty": "technically_confirmed",
        },
    ).json()
    observation = client.post(
        f"/api/cases/{case_id}/observations",
        json={
            "statement": "HTTP 500 was observed after successful authentication.",
            "category": "http_api",
            "certainty": "technically_confirmed",
            "evidence_ids": [evidence["evidence_id"]],
        },
    ).json()
    supported = client.post(
        f"/api/cases/{case_id}/explanations",
        json={
            "statement": "The application service may be failing after authentication.",
            "supporting_observation_ids": [observation["observation_id"]],
        },
    )
    assert supported.status_code == 201
    explanation_id = supported.json()["explanation_id"]

    without_operator = client.post(
        f"/api/cases/{case_id}/explanations/{explanation_id}/status",
        json={"status": "confirmed", "confirmed_by_operator": False},
    )
    confirmed = client.post(
        f"/api/cases/{case_id}/explanations/{explanation_id}/status",
        json={"status": "confirmed", "confirmed_by_operator": True},
    )

    assert without_operator.status_code == 422
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["confirmed_by_operator"] is True
