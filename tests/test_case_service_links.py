from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.catalogue import get_catalogue_repository
from app.catalogue_models import CaseServiceRole, ServiceCatalogueEntry, ServiceKind
from app.domain.models import SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_catalogue_repository import SQLiteCatalogueRepository


def test_case_service_links_are_explicit_and_unique(tmp_path) -> None:
    database = tmp_path / "links.sqlite3"
    case_repository = SQLiteCaseRepository(database)
    catalogue_repository = SQLiteCatalogueRepository(database)
    support_case = case_repository.save(SupportCase(title="Checkout outage", application="Checkout"))
    service = catalogue_repository.save_service(ServiceCatalogueEntry(name="Checkout API", kind=ServiceKind.API))

    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_catalogue_repository] = lambda: catalogue_repository
    client = TestClient(app)

    try:
        payload = {
            "service_id": service.service_id,
            "role": CaseServiceRole.AFFECTED.value,
            "linked_by": "operator@example.test",
            "reason": "Operator confirmed this is the affected service.",
        }
        created = client.post(f"/api/catalogue/cases/{support_case.case_id}/services", json=payload)
        assert created.status_code == 201
        assert created.json()["service_id"] == service.service_id
        assert created.json()["role"] == "affected"

        duplicate = client.post(f"/api/catalogue/cases/{support_case.case_id}/services", json=payload)
        assert duplicate.status_code == 409

        listed = client.get(f"/api/catalogue/cases/{support_case.case_id}/services")
        assert listed.status_code == 200
        assert listed.json()["count"] == 1
        assert listed.json()["links"][0]["reason"] == payload["reason"]
        assert listed.json()["services"][0]["name"] == "Checkout API"
    finally:
        app.dependency_overrides.clear()


def test_case_service_link_requires_existing_case_and_service(tmp_path) -> None:
    database = tmp_path / "links.sqlite3"
    case_repository = SQLiteCaseRepository(database)
    catalogue_repository = SQLiteCatalogueRepository(database)
    support_case = case_repository.save(SupportCase(title="Incident", application="Orders"))
    service = catalogue_repository.save_service(ServiceCatalogueEntry(name="Orders", kind=ServiceKind.APPLICATION))

    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_catalogue_repository] = lambda: catalogue_repository
    client = TestClient(app)
    payload = {"service_id": service.service_id, "role": "context", "linked_by": "operator", "reason": "Investigation context"}

    try:
        missing_case = client.post("/api/catalogue/cases/missing/services", json=payload)
        assert missing_case.status_code == 404
        missing_service = client.post(
            f"/api/catalogue/cases/{support_case.case_id}/services",
            json={**payload, "service_id": "missing"},
        )
        assert missing_service.status_code == 404
    finally:
        app.dependency_overrides.clear()
