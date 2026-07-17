from fastapi.testclient import TestClient

from app.main import app


def test_case_links_asset_is_served() -> None:
    response = TestClient(app).get("/ui/static/case-links.js")
    assert response.status_code == 200
    assert "case-catalogue-panel" in response.text
    assert "item.link.role" in response.text
    assert "item.related_services" in response.text


def test_navigation_loads_case_links_asset() -> None:
    response = TestClient(app).get("/ui/static/navigation.js")
    assert response.status_code == 200
    assert "/ui/static/case-links.js" in response.text
    assert "Service context" in response.text
