from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.handover_analytics import get_handover_repository
from app.handover_analytics import build_handover_activity_report
from app.handover_models import HandoverCaseItem, ShiftHandover
from app.main import app
from app.persistence.sqlite_handover_repository import SQLiteHandoverRepository


def _handover(created_at: datetime) -> ShiftHandover:
    return ShiftHandover(
        shift_label="night",
        prepared_by="operator-a",
        summary="Shift summary",
        created_at=created_at,
        cases=[
            HandoverCaseItem(
                case_id="case-1",
                status_summary="Investigating",
                next_action="Review logs",
                attention_required=True,
                blocker="Waiting for vendor",
            ),
            HandoverCaseItem(
                case_id="case-2",
                status_summary="Monitoring",
                next_action="Check recovery",
            ),
        ],
    )


def test_build_handover_activity_report_filters_window_and_counts_references() -> None:
    now = datetime(2026, 7, 16, 6, tzinfo=timezone.utc)
    report = build_handover_activity_report(
        [_handover(now - timedelta(days=1)), _handover(now - timedelta(days=40))],
        window_days=30,
        now=now,
    )

    assert report.total_handovers == 1
    assert report.total_case_references == 2
    assert report.unique_case_count == 2
    assert report.attention_references == 1
    assert report.blocker_references == 1
    assert report.shift_label_counts == {"night": 1}
    assert report.daily_activity[0].case_references == 2
    assert "do not measure operator performance" in report.disclaimer


def test_handover_activity_api(tmp_path) -> None:
    repository = SQLiteHandoverRepository(tmp_path / "handovers.db")
    repository.save(_handover(datetime.now(timezone.utc)))
    app.dependency_overrides[get_handover_repository] = lambda: repository
    try:
        response = TestClient(app).get("/api/analytics/handover-activity?window_days=7")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["window_days"] == 7
    assert payload["total_handovers"] == 1
    assert payload["attention_references"] == 1


def test_handover_activity_api_rejects_invalid_window() -> None:
    response = TestClient(app).get("/api/analytics/handover-activity?window_days=0")
    assert response.status_code == 422
