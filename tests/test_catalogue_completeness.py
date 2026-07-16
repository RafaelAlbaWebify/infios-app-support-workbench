from fastapi.testclient import TestClient

from app.api.catalogue import get_catalogue_repository
from app.catalogue_completeness import build_catalogue_completeness_report
from app.catalogue_models import Criticality, DependencyType, ServiceCatalogueEntry, ServiceDependency, ServiceKind
from app.main import app
from app.persistence.sqlite_catalogue_repository import SQLiteCatalogueRepository


def test_empty_catalogue_report_is_explicit() -> None:
    report = build_catalogue_completeness_report([], [])
    assert report.status == "empty"
    assert report.service_count == 0
    assert report.services_requiring_attention == 0


def test_report_marks_complete_and_incomplete_services() -> None:
    complete = ServiceCatalogueEntry(
        service_id="service-complete",
        name="Orders",
        kind=ServiceKind.APPLICATION,
        owner_team="Application Support",
        support_contact="support queue",
        criticality=Criticality.HIGH,
        environments=["production"],
        runbook_reference="RB-ORDERS",
        status_page_reference="status/orders",
    )
    incomplete = ServiceCatalogueEntry(
        service_id="service-incomplete",
        name="Orders DB",
        kind=ServiceKind.DATABASE,
    )
    dependency = ServiceDependency(
        source_service_id=complete.service_id,
        target_service_id=incomplete.service_id,
        dependency_type=DependencyType.DATA,
    )

    report = build_catalogue_completeness_report([complete, incomplete], [dependency])

    assert report.status == "attention_required"
    assert report.dependency_count == 1
    assert report.services_requiring_attention == 1
    assert report.services[0].status == "complete"
    assert report.services[1].status == "attention_required"
    assert "owner_team" in report.services[1].missing_information
    assert "dependency_relationships" not in report.services[1].missing_information
    assert report.issue_counts["criticality"] == 1
    assert "do not indicate service failure" in report.interpretation_note


def test_isolated_service_is_reported_as_missing_topology_context() -> None:
    service = ServiceCatalogueEntry(
        service_id="service-isolated",
        name="Standalone Utility",
        kind=ServiceKind.OTHER,
        owner_team="Tools",
        support_contact="tools queue",
        criticality=Criticality.LOW,
        environments=["production"],
        runbook_reference="RB-TOOLS",
        status_page_reference="status/tools",
    )
    report = build_catalogue_completeness_report([service], [])
    assert report.services[0].missing_information == ["dependency_relationships"]


def test_completeness_api_can_include_inactive_services(tmp_path) -> None:
    repository = SQLiteCatalogueRepository(tmp_path / "catalogue.sqlite3")
    active = repository.save_service(
        ServiceCatalogueEntry(
            service_id="service-active",
            name="Active API",
            kind=ServiceKind.API,
            owner_team="API Support",
            support_contact="api queue",
            criticality=Criticality.MEDIUM,
            environments=["production"],
            runbook_reference="RB-API",
            status_page_reference="status/api",
        )
    )
    inactive = repository.save_service(
        ServiceCatalogueEntry(
            service_id="service-inactive",
            name="Retired API",
            kind=ServiceKind.API,
            active=False,
        )
    )
    repository.save_dependency(
        ServiceDependency(
            source_service_id=active.service_id,
            target_service_id=inactive.service_id,
            dependency_type=DependencyType.OPERATIONAL,
        )
    )

    app.dependency_overrides[get_catalogue_repository] = lambda: repository
    client = TestClient(app)

    try:
        active_only = client.get("/api/catalogue/completeness-report")
        assert active_only.status_code == 200
        assert active_only.json()["service_count"] == 1

        all_services = client.get("/api/catalogue/completeness-report?include_inactive=true")
        assert all_services.status_code == 200
        payload = all_services.json()
        assert payload["service_count"] == 2
        assert payload["active_service_count"] == 1
        assert payload["dependency_count"] == 1
    finally:
        app.dependency_overrides.clear()
