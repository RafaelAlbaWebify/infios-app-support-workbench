from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.domain.models import CaseStatus, SupportCase
from app.main import app
from app.operational_trends import build_operational_trend_report
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def test_trend_report_counts_activity_inside_window() -> None:
    now = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    cases = [
        SupportCase(
            title="Recent incident",
            application="Orders",
            severity="high",
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1),
        ),
        SupportCase(
            title="Resolved incident",
            application="Orders",
            severity="medium",
            status=CaseStatus.RESOLVED,
            created_at=now - timedelta(days=5),
            updated_at=now,
        ),
        SupportCase(
            title="Old incident",
            application="Legacy",
            created_at=now - timedelta(days=40),
            updated_at=now - timedelta(days=40),
        ),
    ]

    report = build_operational_trend_report(cases, window_days=30, now=now)

    assert report.created_case_count == 2
    assert report.updated_case_count == 2
    assert report.resolved_or_closed_count == 1
    assert report.created_by_application == {"Orders": 2}
    assert report.created_by_severity == {"high": 1, "medium": 1}
    assert sum(day.created for day in report.daily_activity) == 2
    assert sum(day.resolved_or_closed for day in report.daily_activity) == 1


def test_trends_api_excludes_demo_cases(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "workbench.sqlite3")
    now = datetime.now(timezone.utc)
    repository.save(
        SupportCase(
            title="Real case",
            application="Payments",
            severity="high",
            created_at=now,
            updated_at=now,
        )
    )
    repository.save(
        SupportCase(
            title="Demo case",
            application="Demo",
            is_demo=True,
            created_at=now,
            updated_at=now,
        )
    )
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.get("/api/analytics/operational-trends?window_days=7")
        assert response.status_code == 200
        payload = response.json()
        assert payload["included_case_count"] == 1
        assert payload["created_case_count"] == 1
        assert payload["created_by_application"] == {"Payments": 1}
        assert "performance" in payload["disclaimer"]
    finally:
        app.dependency_overrides.clear()
