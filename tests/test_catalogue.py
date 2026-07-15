from fastapi.testclient import TestClient

from app.api.catalogue import get_catalogue_repository
from app.catalogue_models import DependencyType, ServiceCatalogueEntry, ServiceDependency, ServiceKind
from app.main import app
from app.persistence.sqlite_catalogue_repository import SQLiteCatalogueRepository


def test_repository_persists_services_and_bidirectional_dependency_lookup(tmp_path) -> None:
    repository = SQLiteCatalogueRepository(tmp_path / "catalogue.sqlite3")
    application = repository.save_service(ServiceCatalogueEntry(name="Orders", kind=ServiceKind.APPLICATION))
    database = repository.save_service(ServiceCatalogueEntry(name="Orders DB", kind=ServiceKind.DATABASE))
    dependency = repository.save_dependency(
        ServiceDependency(
            source_service_id=application.service_id,
            target_service_id=database.service_id,
            dependency_type=DependencyType.DATA,
        )
    )

    assert repository.get_service(application.service_id) == application
    assert repository.list_services() == [application, database]
    assert repository.list_dependencies_for_service(application.service_id) == [dependency]
    assert repository.list_dependencies_for_service(database.service_id) == [dependency]


def test_service_cannot_depend_on_itself() -> None:
    try:
        ServiceDependency(
            source_service_id="service-1",
            target_service_id="service-1",
            dependency_type=DependencyType.SYNCHRONOUS,
        )
    except ValueError as exc:
        assert "cannot depend on itself" in str(exc)
    else:
        raise AssertionError("Expected self-dependency validation to fail")


def test_catalogue_api_creates_services_and_dependency(tmp_path) -> None:
    repository = SQLiteCatalogueRepository(tmp_path / "catalogue.sqlite3")
    app.dependency_overrides[get_catalogue_repository] = lambda: repository
    client = TestClient(app)

    try:
        source = client.post(
            "/api/catalogue/services",
            json={
                "name": "Checkout API",
                "kind": "api",
                "criticality": "critical",
                "environments": ["production"],
            },
        )
        target = client.post(
            "/api/catalogue/services",
            json={"name": "Payment Provider", "kind": "external_provider"},
        )
        assert source.status_code == 201
        assert target.status_code == 201

        dependency = client.post(
            f"/api/catalogue/services/{source.json()['service_id']}/dependencies",
            json={
                "target_service_id": target.json()["service_id"],
                "dependency_type": "synchronous",
                "required": True,
            },
        )
        assert dependency.status_code == 201

        listed = client.get(f"/api/catalogue/services/{source.json()['service_id']}/dependencies")
        assert listed.status_code == 200
        assert listed.json()["count"] == 1
        assert listed.json()["dependencies"][0]["target_service_id"] == target.json()["service_id"]
    finally:
        app.dependency_overrides.clear()


def test_dependency_rejects_unknown_target(tmp_path) -> None:
    repository = SQLiteCatalogueRepository(tmp_path / "catalogue.sqlite3")
    source = repository.save_service(ServiceCatalogueEntry(name="Source", kind=ServiceKind.API))
    app.dependency_overrides[get_catalogue_repository] = lambda: repository
    client = TestClient(app)

    try:
        response = client.post(
            f"/api/catalogue/services/{source.service_id}/dependencies",
            json={"target_service_id": "missing", "dependency_type": "network"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Target catalogue service not found"
    finally:
        app.dependency_overrides.clear()
