from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from app.catalogue_models import Criticality, ServiceCatalogueEntry, ServiceDependency


class ServiceCompletenessItem(BaseModel):
    service_id: str
    name: str
    active: bool
    status: str = Field(pattern="^(complete|attention_required)$")
    missing_information: list[str]
    dependency_count: int


class CatalogueCompletenessReport(BaseModel):
    status: str = Field(pattern="^(empty|complete|attention_required)$")
    service_count: int
    active_service_count: int
    dependency_count: int
    services_requiring_attention: int
    issue_counts: dict[str, int]
    services: list[ServiceCompletenessItem]
    interpretation_note: str = (
        "Completeness findings identify missing operational context only; "
        "they do not indicate service failure or incident causation."
    )


def _missing_information(service: ServiceCatalogueEntry, dependency_count: int) -> list[str]:
    missing: list[str] = []
    if not service.owner_team:
        missing.append("owner_team")
    if not service.support_contact:
        missing.append("support_contact")
    if service.criticality is Criticality.UNKNOWN:
        missing.append("criticality")
    if not service.environments:
        missing.append("environments")
    if not service.runbook_reference:
        missing.append("runbook_reference")
    if not service.status_page_reference:
        missing.append("status_page_reference")
    if dependency_count == 0:
        missing.append("dependency_relationships")
    return missing


def build_catalogue_completeness_report(
    services: list[ServiceCatalogueEntry],
    dependencies: list[ServiceDependency],
) -> CatalogueCompletenessReport:
    dependency_counts: Counter[str] = Counter()
    for dependency in dependencies:
        dependency_counts[dependency.source_service_id] += 1
        dependency_counts[dependency.target_service_id] += 1

    items: list[ServiceCompletenessItem] = []
    issue_counts: Counter[str] = Counter()
    for service in services:
        missing = _missing_information(service, dependency_counts[service.service_id])
        issue_counts.update(missing)
        items.append(
            ServiceCompletenessItem(
                service_id=service.service_id,
                name=service.name,
                active=service.active,
                status="attention_required" if missing else "complete",
                missing_information=missing,
                dependency_count=dependency_counts[service.service_id],
            )
        )

    requiring_attention = sum(item.status == "attention_required" for item in items)
    if not services:
        status = "empty"
    elif requiring_attention:
        status = "attention_required"
    else:
        status = "complete"

    return CatalogueCompletenessReport(
        status=status,
        service_count=len(services),
        active_service_count=sum(service.active for service in services),
        dependency_count=len(dependencies),
        services_requiring_attention=requiring_attention,
        issue_counts=dict(sorted(issue_counts.items())),
        services=items,
    )
