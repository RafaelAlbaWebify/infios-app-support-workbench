from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.ui import UI_DIR
from app.domain.models import CaseStatus, SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def _seed(repository: SQLiteCaseRepository) -> tuple[SupportCase, SupportCase, SupportCase]:
    orders = repository.save(
        SupportCase(
            case_id="case-orders-001",
            title="Orders API returns 500",
            application="Order Management",
            status=CaseStatus.INVESTIGATION,
            owner="L1 Support",
        )
    )
    payroll = repository.save(
        SupportCase(
            case_id="case-payroll-002",
            title="Payroll export is blocked",
            application="Payroll Portal",
            status=CaseStatus.BLOCKED,
            owner="Application Support",
        )
    )
    resolved = repository.save(
        SupportCase(
            case_id="case-orders-003",
            title="Orders login recovered",
            application="Order Management",
            status=CaseStatus.RESOLVED,
        )
    )
    return orders, payroll, resolved


def test_repository_searches_case_fields_and_filters_status(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    orders, payroll, _ = _seed(repository)

    cases, count = repository.search(query="order")
    assert count == 2
    assert {case.case_id for case in cases} == {"case-orders-001", "case-orders-003"}

    cases, count = repository.search(query="application support")
    assert count == 1
    assert cases[0].case_id == payroll.case_id

    cases, count = repository.search(status=CaseStatus.INVESTIGATION)
    assert count == 1
    assert cases[0].case_id == orders.case_id

    cases, count = repository.search(query="orders", status=CaseStatus.RESOLVED)
    assert count == 1
    assert cases[0].case_id == "case-orders-003"


def test_case_api_returns_total_filtered_count_before_limit(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    _seed(repository)
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.get("/api/cases", params={"query": "orders", "limit": 1})
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 2
        assert len(payload["cases"]) == 1

        filtered = client.get(
            "/api/cases",
            params={"query": "payroll", "status": "blocked"},
        )
        assert filtered.status_code == 200
        assert filtered.json()["count"] == 1
        assert filtered.json()["cases"][0]["case_id"] == "case-payroll-002"

        invalid_status = client.get("/api/cases", params={"status": "not-a-status"})
        assert invalid_status.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_dashboard_assets_include_accessible_filter_controls() -> None:
    script = (UI_DIR / "app.js").read_text(encoding="utf-8")

    assert "setAttribute('role', 'search')" in script
    assert 'id="case-search"' in script
    assert 'id="case-status-filter"' in script
    assert 'id="clear-case-filters"' in script
    assert "No incidents match the current filters." in script
    assert "document.querySelector('#save-evidence').addEventListener" in script
    assert "loadCases();" in script
