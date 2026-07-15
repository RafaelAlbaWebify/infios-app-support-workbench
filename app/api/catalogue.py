from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.cases import DEFAULT_CASE_DATABASE
from app.catalogue_models import Criticality, DependencyType, ServiceCatalogueEntry, ServiceDependency, ServiceKind
from app.persistence.sqlite_catalogue_repository import SQLiteCatalogueRepository


router = APIRouter(prefix="/api/catalogue", tags=["catalogue"])


class CreateServiceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: ServiceKind
    description: str | None = Field(default=None, max_length=2000)
    owner_team: str | None = Field(default=None, max_length=200)
    support_contact: str | None = Field(default=None, max_length=300)
    criticality: Criticality = Criticality.UNKNOWN
    environments: list[str] = Field(default_factory=list, max_length=20)
    runbook_reference: str | None = Field(default=None, max_length=500)
    status_page_reference: str | None = Field(default=None, max_length=500)


class CreateDependencyRequest(BaseModel):
    target_service_id: str = Field(min_length=1)
    dependency_type: DependencyType
    required: bool = True
    description: str | None = Field(default=None, max_length=1000)


class ServiceListResponse(BaseModel):
    services: list[ServiceCatalogueEntry]
    count: int


class DependencyListResponse(BaseModel):
    dependencies: list[ServiceDependency]
    count: int


@lru_cache(maxsize=1)
def get_catalogue_repository() -> SQLiteCatalogueRepository:
    return SQLiteCatalogueRepository(DEFAULT_CASE_DATABASE)


@router.post("/services", response_model=ServiceCatalogueEntry, status_code=status.HTTP_201_CREATED)
def create_service(
    request: CreateServiceRequest,
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> ServiceCatalogueEntry:
    return repository.save_service(ServiceCatalogueEntry(**request.model_dump()))


@router.get("/services", response_model=ServiceListResponse)
def list_services(
    active_only: bool = Query(default=True),
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> ServiceListResponse:
    services = repository.list_services(active_only=active_only)
    return ServiceListResponse(services=services, count=len(services))


@router.get("/services/{service_id}", response_model=ServiceCatalogueEntry)
def get_service(
    service_id: str,
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> ServiceCatalogueEntry:
    service = repository.get_service(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Catalogue service not found")
    return service


@router.post("/services/{service_id}/dependencies", response_model=ServiceDependency, status_code=status.HTTP_201_CREATED)
def create_dependency(
    service_id: str,
    request: CreateDependencyRequest,
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> ServiceDependency:
    if repository.get_service(service_id) is None:
        raise HTTPException(status_code=404, detail="Source catalogue service not found")
    if repository.get_service(request.target_service_id) is None:
        raise HTTPException(status_code=404, detail="Target catalogue service not found")
    dependency = ServiceDependency(source_service_id=service_id, **request.model_dump())
    return repository.save_dependency(dependency)


@router.get("/services/{service_id}/dependencies", response_model=DependencyListResponse)
def list_dependencies(
    service_id: str,
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> DependencyListResponse:
    if repository.get_service(service_id) is None:
        raise HTTPException(status_code=404, detail="Catalogue service not found")
    dependencies = repository.list_dependencies_for_service(service_id)
    return DependencyListResponse(dependencies=dependencies, count=len(dependencies))
