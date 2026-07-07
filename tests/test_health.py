from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_samples_endpoint_lists_500_login_sample() -> None:
    response = client.get("/api/samples")
    assert response.status_code == 200
    assert "incident-500-login.json" in response.json()["samples"]
