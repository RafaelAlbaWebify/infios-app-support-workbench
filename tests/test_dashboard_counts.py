from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.domain.models import CaseStatus, SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def test_dashboard_counts_group_operational_statuses(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    now = datetime.now(timezone.utc)
    for case_id, case_status in (
        ("case-new", CaseStatus.NEW),
        ("case-wait-user", CaseStatus.WAITING_FOR_USER),
        ("case-blocked", CaseStatus.BLOCKED),
        ("case-escalated", CaseStatus.ESCALATED),
        ("case-recovery", CaseStatus.RECOVERY_VALIDATION),
        ("case-resolved", CaseStatus.RESOLVED),
        ("case-closed", CaseStatus.CLOSED),
    ):
        repository.save(
            SupportCase(
                case_id=case_id,
                title=case_id,
                application="Sample App",
                status=case_status,
                updated_at=now,
            )
        )

    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)
    try:
        response = client.get("/api/cases/dashboard")
        assert response.status_code == 200
        payload = response.json()
        assert payload["open_cases"] == 5
        assert payload["waiting_cases"] == 2
        assert payload["escalated_cases"] == 1
        assert payload["recovery_validation_cases"] == 1
        assert payload["resolved_today"] == 1
        assert payload["generated_at"]
    finally:
        app.dependency_overrides.clear()


def test_dashboard_counter_assets_are_served_and_loaded() -> None:
    client = TestClient(app)
    dashboard = client.get("/ui/static/dashboard.js")
    navigation = client.get("/ui/static/navigation.js")

    assert dashboard.status_code == 200
    assert "Operational case counters" in dashboard.text
    assert "/api/cases/dashboard" in dashboard.text
    assert "Resolved today" in dashboard.text
    assert navigation.status_code == 200
    assert "/ui/static/dashboard.js" in navigation.text
