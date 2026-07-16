from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.catalogue import get_catalogue_repository
from app.catalogue_models import (
    CaseServiceLink,
    CaseServiceRole,
    DependencyType,
    ServiceCatalogueEntry,
    ServiceDependency,
    ServiceKind,
)
from app.dependency_context import build_case_dependency_context
from app.domain.models import SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_catalogue_repository import SQLiteCatalogueRepository


def test_builds_upstream_and_downstream_context_without_asserting_cause() -> None:
    application = ServiceCatalogueEntry(
        service_id="service-app",
        name="Orders",
        kind=ServiceKind.APPLICATION,
        owner_team="Application Support",
        support_contact="support queue",
        environments=["production"],
        runbook_reference="RB-ORDERS",
        status_page_reference="status/orders",
    )
    database = ServiceCatalogueEntry(service_id="service-db", name="Orders DB", kind=ServiceKind.DATABASE)
    consumer = ServiceCatalogueEntry(service_id="service-consumer", name="Warehouse", kind=ServiceKind.APPLICATION)
    link = CaseServiceLink(
        case_id="case-1",
        service_id=application.service_id,
        role=CaseServiceRole.AFFECTED,
        linked_by="operator",
        reason="Users report failures in Orders.",
    )
    dependencies = [
        ServiceDependency(
            dependency_id="dependency-db",
            source_service_id=application.service_id,
            target_service_id=database.service_id,
            dependency_type=DependencyType.DATA,
        ),
        ServiceDependency(
            dependency_id="dependency-consumer",
            source_service_id=consumer.service_id,
            target_service_id=application.service_id,
            dependency_type=DependencyType.SYNCHRONOUS,
        ),
    ]

    report = build_case_dependency_context(
        case_id="case-1",
        links=[link],
        services_by_id={item.service_id: item for item in [application, database, consumer]},
        dependencies=dependencies,
    )

    assert report.status == "context_available"
    assert report.linked_service_count == 1
    assert report.dependency_count == 2
    assert [(item.direction, item.service.service_id) for item in report.linked_services[0].related_services] == [
        ("upstream", "service-db"),
        ("downstream", "service-consumer"),
    ]
    assert "do not prove" in report.interpretation_note


def test_reports_no_links_and_missing_catalogue_metadata() -> None:
    no_links = build_case_dependency_context("case-empty", [], {}, [])
    assert no_links.status == "no_catalogue_links"
    assert no_links.linked_service_count == 0

    service = ServiceCatalogueEntry(service_id="service-incomplete", name="Incomplete", kind=ServiceKind.API)
    link = CaseServiceLink(
        case_id="case-2",
        service_id=service.service_id,
        role=CaseServiceRole.CONTEXT,
        linked_by="operator",
        reason="Potentially relevant service.",
    )
    incomplete = build_case_dependency_context("case-2", [link], {service.service_id: service}, [])
    assert incomplete.status == "attention_required"
    assert "owner_team" in incomplete.linked_services[0].missing_information
    assert f"{service.service_id}:runbook_reference" in incomplete.missing_information


def test_dependency_context_api_resolves_linked_and_related_services(tmp_path) -> None:
    database_path = tmp_path / "context.sqlite3"
    case_repository = SQLiteCaseRepository(database_path)
    catalogue_repository = SQLiteCatalogueRepository(database_path)
    support_case = case_repository.save(SupportCase(case_id="case-context", title="Checkout errors", application="Checkout"))
    application = catalogue_repository.save_service(
        ServiceCatalogueEntry(
            service_id="service-checkout",
            name="Checkout",
            kind=ServiceKind.APPLICATION,
            owner_team="Payments Support",
            support_contact="payments queue",
            environments=["production"],
            runbook_reference="RB-CHECKOUT",
            status_page_reference="status/checkout",
        )
    )
    provider = catalogue_repository.save_service(
        ServiceCatalogueEntry(service_id="service-provider", name="Payment Provider", kind=ServiceKind.EXTERNAL_PROVIDER)
    )
    catalogue_repository.save_dependency(
        ServiceDependency(
            source_service_id=application.service_id,
            target_service_id=provider.service_id,
            dependency_type=DependencyType.SYNCHRONOUS,
        )
    )
    catalogue_repository.save_case_link(
        CaseServiceLink(
            case_id=support_case.case_id,
            service_id=application.service_id,
            role=CaseServiceRole.AFFECTED,
            linked_by="analyst",
            reason="Checkout is the reported affected service.",
        )
    )

    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_catalogue_repository] = lambda: catalogue_repository
    client = TestClient(app)

    try:
        response = client.get(f"/api/catalogue/cases/{support_case.case_id}/dependency-context")
        assert response.status_code == 200
        payload = response.json()
        assert payload["linked_service_count"] == 1
        assert payload["dependency_count"] == 1
        assert payload["linked_services"][0]["service"]["service_id"] == application.service_id
        assert payload["linked_services"][0]["related_services"][0]["service"]["service_id"] == provider.service_id
        assert payload["linked_services"][0]["related_services"][0]["direction"] == "upstream"
    finally:
        app.dependency_overrides.clear()
