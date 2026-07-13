from fastapi.testclient import TestClient

from app.main import app


def test_guided_workbench_is_served_at_root() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "INFIOS" in response.text
    assert "Guided L1 mode" in response.text
    assert "Recent incidents" in response.text
    assert "What is happening?" in response.text
    assert "Unknown is valid" in response.text
    assert "New incident" in response.text
    assert "Back to recent incidents" in response.text


def test_guided_workbench_assets_are_served() -> None:
    client = TestClient(app)

    stylesheet = client.get("/ui/static/styles.css")
    script = client.get("/ui/static/app.js")

    assert stylesheet.status_code == 200
    assert "--accent" in stylesheet.text
    assert ".case-card" in stylesheet.text
    assert script.status_code == 200
    assert "/api/cases?limit=20" in script.text
    assert "openCase" in script.text
    assert "/summary" in script.text
    assert "redacted: false" in script.text
    assert "loadCases();" in script.text


def test_case_api_contract_supports_dashboard_and_resume() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/cases",
        json={"title": "Orders page fails", "application": "Order Management"},
    )

    assert created.status_code == 201
    case_id = created.json()["case_id"]

    listed = client.get("/api/cases?limit=20")
    reopened = client.get(f"/api/cases/{case_id}")
    summary = client.get(f"/api/cases/{case_id}/summary")

    assert listed.status_code == 200
    assert any(item["case_id"] == case_id for item in listed.json()["cases"])
    assert reopened.status_code == 200
    assert reopened.json()["title"] == "Orders page fails"
    assert summary.status_code == 200
    assert summary.json()["case"]["case_id"] == case_id


def test_api_documentation_remains_available() -> None:
    response = TestClient(app).get("/docs")

    assert response.status_code == 200
    assert "Swagger UI" in response.text
