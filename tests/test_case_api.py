from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def test_create_list_and_get_case(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        create_response = client.post(
            "/api/cases",
            json={
                "title": "Orders page fails after login",
                "application": "Order Management",
                "environment": "test",
                "severity": "high",
                "impact": "Order submission is blocked",
                "owner": "L1 Support",
                "affected_scope": "Three users",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["status"] == "new"
        assert created["title"] == "Orders page fails after login"
        assert created["case_id"].startswith("case-")

        list_response = client.get("/api/cases")
        assert list_response.status_code == 200
        listing = list_response.json()
        assert listing["count"] == 1
        assert listing["cases"][0]["case_id"] == created["case_id"]

        get_response = client.get(f"/api/cases/{created['case_id']}")
        assert get_response.status_code == 200
        assert get_response.json() == created
    finally:
        app.dependency_overrides.clear()


def test_case_api_returns_not_found_for_unknown_case(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.get("/api/cases/case-does-not-exist")
        assert response.status_code == 404
        assert response.json() == {"detail": "Support case not found"}
    finally:
        app.dependency_overrides.clear()


def test_case_api_validates_required_fields_and_limit(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        missing_title = client.post(
            "/api/cases",
            json={"application": "Order Management"},
        )
        assert missing_title.status_code == 422

        invalid_limit = client.get("/api/cases?limit=0")
        assert invalid_limit.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_legacy_health_endpoint_remains_available(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    finally:
        app.dependency_overrides.clear()
