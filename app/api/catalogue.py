from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.catalogue_completeness import CatalogueCompletenessReport, build_catalogue_completeness_report
from app.catalogue_models import CaseServiceLink, CaseServiceRole, Criticality, DependencyType, ServiceCatalogueEntry, ServiceDependency, ServiceKind
from app.dependency_context import CaseDependencyContextReport, build_case_dependency_context
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
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


class CreateCaseServiceLinkRequest(BaseModel):
    service_id: str = Field(min_length=1)
    role: CaseServiceRole
    linked_by: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)


class ServiceListResponse(BaseModel):
    services: list[ServiceCatalogueEntry]
    count: int


class DependencyListResponse(BaseModel):
    dependencies: list[ServiceDependency]
    count: int


class CaseServiceLinkListResponse(BaseModel):
    links: list[CaseServiceLink]
    services: list[ServiceCatalogueEntry]
    count: int


@lru_cache(maxsize=1)
def get_catalogue_repository() -> SQLiteCatalogueRepository:
    return SQLiteCatalogueRepository(DEFAULT_CASE_DATABASE)


@router.post("/services", response_model=ServiceCatalogueEntry, status_code=status.HTTP_201_CREATED)
def create_service(request: CreateServiceRequest, repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository)) -> ServiceCatalogueEntry:
    return repository.save_service(ServiceCatalogueEntry(**request.model_dump()))


@router.get("/services", response_model=ServiceListResponse)
def list_services(active_only: bool = Query(default=True), repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository)) -> ServiceListResponse:
    services = repository.list_services(active_only=active_only)
    return ServiceListResponse(services=services, count=len(services))


@router.get("/completeness-report", response_model=CatalogueCompletenessReport)
def catalogue_completeness_report(
    include_inactive: bool = Query(default=False),
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> CatalogueCompletenessReport:
    return build_catalogue_completeness_report(
        services=repository.list_services(active_only=not include_inactive),
        dependencies=repository.list_dependencies(),
    )


@router.get("/services/{service_id}", response_model=ServiceCatalogueEntry)
def get_service(service_id: str, repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository)) -> ServiceCatalogueEntry:
    service = repository.get_service(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Catalogue service not found")
    return service


@router.post("/services/{service_id}/dependencies", response_model=ServiceDependency, status_code=status.HTTP_201_CREATED)
def create_dependency(service_id: str, request: CreateDependencyRequest, repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository)) -> ServiceDependency:
    if repository.get_service(service_id) is None:
        raise HTTPException(status_code=404, detail="Source catalogue service not found")
    if repository.get_service(request.target_service_id) is None:
        raise HTTPException(status_code=404, detail="Target catalogue service not found")
    return repository.save_dependency(ServiceDependency(source_service_id=service_id, **request.model_dump()))


@router.get("/services/{service_id}/dependencies", response_model=DependencyListResponse)
def list_dependencies(service_id: str, repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository)) -> DependencyListResponse:
    if repository.get_service(service_id) is None:
        raise HTTPException(status_code=404, detail="Catalogue service not found")
    dependencies = repository.list_dependencies_for_service(service_id)
    return DependencyListResponse(dependencies=dependencies, count=len(dependencies))


@router.post("/cases/{case_id}/services", response_model=CaseServiceLink, status_code=status.HTTP_201_CREATED)
def link_case_to_service(
    case_id: str,
    request: CreateCaseServiceLinkRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> CaseServiceLink:
    if case_repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    if repository.get_service(request.service_id) is None:
        raise HTTPException(status_code=404, detail="Catalogue service not found")
    try:
        return repository.save_case_link(CaseServiceLink(case_id=case_id, **request.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/cases/{case_id}/services", response_model=CaseServiceLinkListResponse)
def list_case_services(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> CaseServiceLinkListResponse:
    if case_repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    links = repository.list_case_links(case_id)
    services = [service for link in links if (service := repository.get_service(link.service_id)) is not None]
    return CaseServiceLinkListResponse(links=links, services=services, count=len(links))


@router.get("/cases/{case_id}/dependency-context", response_model=CaseDependencyContextReport)
def case_dependency_context(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    repository: SQLiteCatalogueRepository = Depends(get_catalogue_repository),
) -> CaseDependencyContextReport:
    if case_repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")

    links = repository.list_case_links(case_id)
    services_by_id: dict[str, ServiceCatalogueEntry] = {}
    dependencies_by_id: dict[str, ServiceDependency] = {}

    for link in links:
        linked_service = repository.get_service(link.service_id)
        if linked_service is not None:
            services_by_id[linked_service.service_id] = linked_service
        for dependency in repository.list_dependencies_for_service(link.service_id):
            dependencies_by_id[dependency.dependency_id] = dependency
            for related_service_id in (dependency.source_service_id, dependency.target_service_id):
                related_service = repository.get_service(related_service_id)
                if related_service is not None:
                    services_by_id[related_service.service_id] = related_service

    return build_case_dependency_context(
        case_id=case_id,
        links=links,
        services_by_id=services_by_id,
        dependencies=list(dependencies_by_id.values()),
    )
