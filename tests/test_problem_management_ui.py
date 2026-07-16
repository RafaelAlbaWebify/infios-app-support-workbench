from fastapi.testclient import TestClient

from app.main import app


def test_problem_management_page_is_served() -> None:
    response = TestClient(app).get("/problems")

    assert response.status_code == 200
    assert "Problem records" in response.text
    assert "/ui/static/problems.js" in response.text
    assert "Closure readiness" in response.text
