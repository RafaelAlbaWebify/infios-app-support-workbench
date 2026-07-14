from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.ui import UI_DIR
from app.domain.models import CaseStatus, SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def _case(
    case_id: str,
    *,
    owner: str | None,
    created_hours_ago: int,
    updated_hours_ago: int,
) -> SupportCase:
    now = datetime.now(timezone.utc)
    return SupportCase(
        case_id=case_id,
        title=f"Incident {case_id}",
        application="Workload Test",
        status=CaseStatus.INVESTIGATION,
        owner=owner,
        created_at=now - timedelta(hours=created_hours_ago),
        updated_at=now - timedelta(hours=updated_hours_ago),
    )


def test_repository_filters_assigned_unassigned_and_exact_owner(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    repository.save(_case("case-a", owner="L1 Support", created_hours_ago=5, updated_hours_ago=1))
    repository.save(_case("case-b", owner=None, created_hours_ago=8, updated_hours_ago=2))
    repository.save(_case("case-c", owner="Application Support", created_hours_ago=10, updated_hours_ago=3))

    assigned, assigned_count = repository.search(owner="__assigned__")
    assert assigned_count == 2
    assert {item.case_id for item in assigned} == {"case-a", "case-c"}

    unassigned, unassigned_count = repository.search(owner="__unassigned__")
    assert unassigned_count == 1
    assert unassigned[0].case_id == "case-b"

    exact, exact_count = repository.search(owner="l1 support")
    assert exact_count == 1
    assert exact[0].case_id == "case-a"


def test_repository_supports_safe_created_and_updated_sorting(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    repository.save(_case("case-a", owner=None, created_hours_ago=12, updated_hours_ago=1))
    repository.save(_case("case-b", owner=None, created_hours_ago=4, updated_hours_ago=8))

    newest_updated, _ = repository.search(sort="updated_desc")
    assert [item.case_id for item in newest_updated] == ["case-a", "case-b"]

    oldest_updated, _ = repository.search(sort="updated_asc")
    assert [item.case_id for item in oldest_updated] == ["case-b", "case-a"]

    newest_created, _ = repository.search(sort="created_desc")
    assert [item.case_id for item in newest_created] == ["case-b", "case-a"]

    oldest_created, _ = repository.search(sort="created_asc")
    assert [item.case_id for item in oldest_created] == ["case-a", "case-b"]


def test_case_api_validates_sort_and_combines_owner_filter(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    repository.save(_case("case-a", owner="L1 Support", created_hours_ago=12, updated_hours_ago=1))
    repository.save(_case("case-b", owner=None, created_hours_ago=4, updated_hours_ago=8))
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.get(
            "/api/cases",
            params={"owner": "__unassigned__", "sort": "created_desc"},
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["cases"][0]["case_id"] == "case-b"

        invalid = client.get("/api/cases", params={"sort": "unsafe sql"})
        assert invalid.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_dashboard_assets_include_workload_filters_and_age_labels() -> None:
    script = (UI_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="case-owner-filter"' in script
    assert 'id="case-owner-name"' in script
    assert 'id="case-sort"' in script
    assert "__unassigned__" in script
    assert "Stale ·" in script
    assert "Ageing ·" in script
    assert "parameters.set('sort', filters.sort)" in script
    assert "document.querySelector('#save-evidence').addEventListener" in script
    assert script.rstrip().endswith("loadCases();")
