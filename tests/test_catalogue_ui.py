from fastapi.testclient import TestClient

from app.main import app


def test_catalogue_route_serves_page() -> None:
    response = TestClient(app).get("/catalogue")
    assert response.status_code == 200
    assert "Service catalogue" in response.text
    assert "operational context only" in response.text
