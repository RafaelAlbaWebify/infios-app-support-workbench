from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.handovers import get_handover_repository
from app.domain.models import SupportCase
from app.handover_models import HandoverCaseItem, ShiftHandover
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_handover_repository import SQLiteHandoverRepository


def test_shift_handover_requires_unique_case_ids() -> None:
    try:
        ShiftHandover(
            shift_label="Night shift",
            prepared_by="operator",
            summary="Two references to the same case.",
            cases=[
                HandoverCaseItem(case_id="case-1", status_summary="Investigating", next_action="Check logs"),
                HandoverCaseItem(case_id="case-1", status_summary="Still investigating", next_action="Escalate"),
            ],
        )
    except ValueError as exc:
        assert "same case more than once" in str(exc)
    else:
        raise AssertionError("Expected duplicate case validation to fail")


def test_repository_persists_immutable_handover_snapshots(tmp_path) -> None:
    repository = SQLiteHandoverRepository(tmp_path / "handovers.sqlite3")
    handover = ShiftHandover(
        handover_id="handover-test",
        shift_label="Morning shift",
        prepared_by="analyst",
        summary="One active incident.",
        cases=[
            HandoverCaseItem(
                case_id="case-1",
                status_summary="Evidence collection in progress.",
                next_action="Compare successful and failed requests.",
                attention_required=True,
            )
        ],
    )

    repository.save(handover)
    assert repository.get(handover.handover_id) == handover
    assert repository.list_recent() == [handover]

    try:
        repository.save(handover)
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Expected immutable duplicate handover save to fail")


def test_handover_api_validates_case_references_and_lists_snapshots(tmp_path) -> None:
    database_path = tmp_path / "handovers.sqlite3"
    case_repository = SQLiteCaseRepository(database_path)
    handover_repository = SQLiteHandoverRepository(database_path)
    support_case = case_repository.save(
        SupportCase(case_id="case-handover", title="Intermittent checkout", application="Checkout")
    )

    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_handover_repository] = lambda: handover_repository
    client = TestClient(app)

    try:
        missing = client.post(
            "/api/handovers",
            json={
                "shift_label": "Night shift",
                "prepared_by": "analyst",
                "summary": "Missing case reference.",
                "cases": [
                    {
                        "case_id": "case-missing",
                        "status_summary": "Unknown",
                        "next_action": "Verify case identifier",
                    }
                ],
            },
        )
        assert missing.status_code == 422
        assert missing.json()["detail"]["missing_case_ids"] == ["case-missing"]

        created = client.post(
            "/api/handovers",
            json={
                "shift_label": "Night shift",
                "prepared_by": "analyst",
                "summary": "Checkout incident remains under investigation.",
                "cases": [
                    {
                        "case_id": support_case.case_id,
                        "status_summary": "Failures are intermittent; no cause confirmed.",
                        "next_action": "Collect matched success and failure samples.",
                        "blocker": "Awaiting production timestamps.",
                        "attention_required": True,
                    }
                ],
            },
        )
        assert created.status_code == 201
        payload = created.json()
        assert payload["prepared_by"] == "analyst"
        assert payload["cases"][0]["case_id"] == support_case.case_id

        listed = client.get("/api/handovers")
        assert listed.status_code == 200
        assert listed.json()["count"] == 1

        fetched = client.get(f"/api/handovers/{payload['handover_id']}")
        assert fetched.status_code == 200
        assert fetched.json() == payload
    finally:
        app.dependency_overrides.clear()
