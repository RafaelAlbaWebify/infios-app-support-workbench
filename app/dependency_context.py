from __future__ import annotations

from pydantic import BaseModel, Field

from app.catalogue_models import CaseServiceLink, ServiceCatalogueEntry, ServiceDependency


class RelatedServiceContext(BaseModel):
    dependency: ServiceDependency
    direction: str = Field(pattern="^(upstream|downstream)$")
    service: ServiceCatalogueEntry


class LinkedServiceContext(BaseModel):
    link: CaseServiceLink
    service: ServiceCatalogueEntry
    related_services: list[RelatedServiceContext] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class CaseDependencyContextReport(BaseModel):
    case_id: str
    status: str = Field(pattern="^(no_catalogue_links|context_available|attention_required)$")
    linked_service_count: int
    dependency_count: int
    linked_services: list[LinkedServiceContext]
    missing_information: list[str]
    interpretation_note: str = (
        "Catalogue relationships provide investigation and ownership context only; "
        "they do not prove that a dependency caused the incident."
    )


def _missing_service_information(service: ServiceCatalogueEntry) -> list[str]:
    missing: list[str] = []
    if not service.owner_team:
        missing.append("owner_team")
    if not service.support_contact:
        missing.append("support_contact")
    if not service.environments:
        missing.append("environments")
    if not service.runbook_reference:
        missing.append("runbook_reference")
    if not service.status_page_reference:
        missing.append("status_page_reference")
    return missing


def build_case_dependency_context(
    case_id: str,
    links: list[CaseServiceLink],
    services_by_id: dict[str, ServiceCatalogueEntry],
    dependencies: list[ServiceDependency],
) -> CaseDependencyContextReport:
    linked_context: list[LinkedServiceContext] = []
    case_missing: list[str] = []
    dependency_ids: set[str] = set()

    for link in links:
        service = services_by_id.get(link.service_id)
        if service is None:
            case_missing.append(f"linked_service_missing:{link.service_id}")
            continue

        related: list[RelatedServiceContext] = []
        for dependency in dependencies:
            if dependency.source_service_id == service.service_id:
                related_service = services_by_id.get(dependency.target_service_id)
                if related_service is None:
                    case_missing.append(f"dependency_target_missing:{dependency.target_service_id}")
                    continue
                direction = "upstream"
            elif dependency.target_service_id == service.service_id:
                related_service = services_by_id.get(dependency.source_service_id)
                if related_service is None:
                    case_missing.append(f"dependency_source_missing:{dependency.source_service_id}")
                    continue
                direction = "downstream"
            else:
                continue

            dependency_ids.add(dependency.dependency_id)
            related.append(
                RelatedServiceContext(
                    dependency=dependency,
                    direction=direction,
                    service=related_service,
                )
            )

        missing = _missing_service_information(service)
        linked_context.append(
            LinkedServiceContext(
                link=link,
                service=service,
                related_services=related,
                missing_information=missing,
            )
        )
        case_missing.extend(f"{service.service_id}:{item}" for item in missing)

    if not links:
        status = "no_catalogue_links"
        case_missing.append("No catalogue services are linked to this case.")
    elif case_missing:
        status = "attention_required"
    else:
        status = "context_available"

    return CaseDependencyContextReport(
        case_id=case_id,
        status=status,
        linked_service_count=len(linked_context),
        dependency_count=len(dependency_ids),
        linked_services=linked_context,
        missing_information=sorted(set(case_missing)),
    )
