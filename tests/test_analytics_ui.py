from fastapi.testclient import TestClient

from app.main import app


def test_analytics_page_is_served() -> None:
    response = TestClient(app).get("/analytics")
    assert response.status_code == 200
    assert "Support analytics" in response.text
    assert "Read-only analytics" in response.text
    assert "/ui/static/analytics.js" in response.text


def test_navigation_script_links_analytics() -> None:
    response = TestClient(app).get("/ui/static/navigation.js")
    assert response.status_code == 200
    assert "'Analytics'" in response.text
    assert "/analytics" in response.text
