from fastapi.testclient import TestClient

from app.main import app


def test_guided_workbench_is_served_at_root() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "INFIOS" in response.text
    assert "Guided L1 mode" in response.text
    assert "What is happening?" in response.text
    assert "Unknown is valid" in response.text
    assert "Create incident and continue" in response.text


def test_guided_workbench_assets_are_served() -> None:
    client = TestClient(app)

    stylesheet = client.get("/ui/static/styles.css")
    script = client.get("/ui/static/app.js")

    assert stylesheet.status_code == 200
    assert "--accent" in stylesheet.text
    assert script.status_code == 200
    assert "/api/cases" in script.text
    assert "/summary" in script.text
    assert "redacted: false" in script.text


def test_api_documentation_remains_available() -> None:
    response = TestClient(app).get("/docs")

    assert response.status_code == 200
    assert "Swagger UI" in response.text
