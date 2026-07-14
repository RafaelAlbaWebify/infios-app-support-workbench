from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def test_case_metadata_update_persists_history_and_timestamp(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        created = client.post(
            "/api/cases",
            json={"title": "Orders fail", "application": "Order Management"},
        ).json()

        response = client.patch(
            f"/api/cases/{created['case_id']}",
            json={
                "environment": "production",
                "severity": "high",
                "owner": "Application Support",
                "changed_by": "L1 Support",
            },
        )

        assert response.status_code == 200
        updated = response.json()
        assert updated["environment"] == "production"
        assert updated["severity"] == "high"
        assert updated["owner"] == "Application Support"
        assert updated["updated_at"] != created["updated_at"]
        assert len(updated["metadata_changes"]) == 1
        change = updated["metadata_changes"][0]
        assert change["changed_by"] == "L1 Support"
        assert change["fields"] == ["environment", "severity", "owner"]
        assert change["summary"] == "Updated environment, severity, owner"

        reopened = client.get(f"/api/cases/{created['case_id']}").json()
        assert reopened == updated
    finally:
        app.dependency_overrides.clear()


def test_case_metadata_update_rejects_noop_empty_and_unknown_case(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        created = client.post(
            "/api/cases",
            json={"title": "Orders fail", "application": "Order Management"},
        ).json()

        empty = client.patch(
            f"/api/cases/{created['case_id']}",
            json={"changed_by": "L1 Support"},
        )
        assert empty.status_code == 422

        noop = client.patch(
            f"/api/cases/{created['case_id']}",
            json={"title": "Orders fail", "changed_by": "L1 Support"},
        )
        assert noop.status_code == 409

        missing = client.patch(
            "/api/cases/case-does-not-exist",
            json={"owner": "L2", "changed_by": "L1 Support"},
        )
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_metadata_frontend_module_is_served_and_loaded() -> None:
    client = TestClient(app)
    metadata = client.get("/ui/static/metadata.js")
    navigation = client.get("/ui/static/navigation.js")

    assert metadata.status_code == 200
    assert "Edit case details" in metadata.text
    assert "metadata_changes" in metadata.text
    assert "method: 'PATCH'" in metadata.text
    assert navigation.status_code == 200
    assert "/ui/static/metadata.js" in navigation.text
