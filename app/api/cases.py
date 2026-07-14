from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator

from app.domain.models import CaseArchiveEvent, CaseMetadataChange, CaseStatus, SupportCase
from app.persistence.sqlite_case_repository import SQLiteCaseRepository

router = APIRouter(prefix="/api/cases", tags=["cases"])

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CASE_DATABASE = ROOT_DIR / "runs" / "infios-cases.sqlite3"


class CaseSort(str, Enum):
    UPDATED_DESC = "updated_desc"
    UPDATED_ASC = "updated_asc"
    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"


class CaseKind(str, Enum):
    ALL = "all"
    REAL = "real"
    DEMO = "demo"


class ArchiveState(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ALL = "all"


class CreateCaseRequest(BaseModel):
    title: str = Field(min_length=1)
    application: str = Field(min_length=1)
    environment: str = "unknown"
    severity: str = "unknown"
    impact: str = "unknown"
    owner: str | None = None
    affected_scope: str = "unknown"
    is_demo: bool = False


class UpdateCaseMetadataRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    application: str | None = Field(default=None, min_length=1)
    environment: str | None = Field(default=None, min_length=1)
    severity: str | None = Field(default=None, min_length=1)
    impact: str | None = Field(default=None, min_length=1)
    owner: str | None = None
    affected_scope: str | None = Field(default=None, min_length=1)
    changed_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_at_least_one_metadata_field(self) -> UpdateCaseMetadataRequest:
        metadata_fields = (
            self.title,
            self.application,
            self.environment,
            self.severity,
            self.impact,
            self.affected_scope,
        )
        if not any(value is not None for value in metadata_fields) and "owner" not in self.model_fields_set:
            raise ValueError("At least one case metadata field must be supplied.")
        return self


class ArchiveCaseRequest(BaseModel):
    performed_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class CaseListResponse(BaseModel):
    cases: list[SupportCase]
    count: int


class DashboardCountsResponse(BaseModel):
    open_cases: int
    waiting_cases: int
    escalated_cases: int
    recovery_validation_cases: int
    resolved_today: int
    generated_at: datetime


@lru_cache(maxsize=1)
def get_case_repository() -> SQLiteCaseRepository:
    return SQLiteCaseRepository(DEFAULT_CASE_DATABASE)


@router.post("", response_model=SupportCase, status_code=status.HTTP_201_CREATED)
def create_case(
    request: CreateCaseRequest,
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> SupportCase:
    support_case = SupportCase(
        title=request.title,
        application=request.application,
        environment=request.environment,
        status=CaseStatus.NEW,
        severity=request.severity,
        impact=request.impact,
        owner=request.owner,
        affected_scope=request.affected_scope,
        is_demo=request.is_demo,
    )
    return repository.save(support_case)


@router.get("", response_model=CaseListResponse)
def list_cases(
    limit: int = Query(default=50, ge=1, le=200),
    query: str | None = Query(default=None, max_length=200),
    case_status: CaseStatus | None = Query(default=None, alias="status"),
    owner: str | None = Query(default=None, max_length=200),
    sort: CaseSort = Query(default=CaseSort.UPDATED_DESC),
    case_kind: CaseKind = Query(default=CaseKind.ALL),
    archive_state: ArchiveState = Query(default=ArchiveState.ACTIVE),
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> CaseListResponse:
    cases, count = repository.search(
        limit=limit,
        query=query,
        status=case_status,
        owner=owner,
        sort=sort.value,
        case_kind=case_kind.value,
        archive_state=archive_state.value,
    )
    return CaseListResponse(cases=cases, count=count)


@router.get("/dashboard", response_model=DashboardCountsResponse)
def dashboard_counts(
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> DashboardCountsResponse:
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    counts = repository.dashboard_counts(resolved_since=start_of_day)
    return DashboardCountsResponse(
        open_cases=counts["open_cases"],
        waiting_cases=counts["waiting_cases"],
        escalated_cases=counts["escalated_cases"],
        recovery_validation_cases=counts["recovery_validation_cases"],
        resolved_today=counts["resolved_since"],
        generated_at=now,
    )


@router.get("/{case_id}", response_model=SupportCase)
def get_case(
    case_id: str,
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> SupportCase:
    support_case = repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    return support_case


@router.patch("/{case_id}", response_model=SupportCase)
def update_case_metadata(
    case_id: str,
    request: UpdateCaseMetadataRequest,
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> SupportCase:
    support_case = repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    if support_case.archived_at is not None:
        raise HTTPException(status_code=409, detail="Restore the case before editing metadata.")

    update_values = request.model_dump(exclude={"changed_by"}, exclude_unset=True)
    changed_fields = [
        field_name
        for field_name, value in update_values.items()
        if getattr(support_case, field_name) != value
    ]
    if not changed_fields:
        raise HTTPException(status_code=409, detail="The supplied metadata does not change the case.")

    now = datetime.now(timezone.utc)
    history = [
        *support_case.metadata_changes,
        CaseMetadataChange(
            changed_at=now,
            changed_by=request.changed_by,
            fields=changed_fields,
            summary="Updated " + ", ".join(field.replace("_", " ") for field in changed_fields),
        ),
    ]
    updated = support_case.model_copy(
        update={
            **{field: update_values[field] for field in changed_fields},
            "metadata_changes": history,
            "updated_at": now,
        }
    )
    return repository.save(updated)


@router.post("/{case_id}/archive", response_model=SupportCase)
def archive_case(
    case_id: str,
    request: ArchiveCaseRequest,
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> SupportCase:
    support_case = repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    if support_case.archived_at is not None:
        raise HTTPException(status_code=409, detail="Support case is already archived")
    now = datetime.now(timezone.utc)
    event = CaseArchiveEvent(
        action="archived",
        occurred_at=now,
        performed_by=request.performed_by,
        reason=request.reason,
    )
    archived = support_case.model_copy(
        update={
            "archived_at": now,
            "archived_by": request.performed_by,
            "archive_reason": request.reason,
            "archive_history": [*support_case.archive_history, event],
            "updated_at": now,
        }
    )
    return repository.save(archived)


@router.post("/{case_id}/restore", response_model=SupportCase)
def restore_case(
    case_id: str,
    request: ArchiveCaseRequest,
    repository: SQLiteCaseRepository = Depends(get_case_repository),
) -> SupportCase:
    support_case = repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")
    if support_case.archived_at is None:
        raise HTTPException(status_code=409, detail="Support case is not archived")
    now = datetime.now(timezone.utc)
    event = CaseArchiveEvent(
        action="restored",
        occurred_at=now,
        performed_by=request.performed_by,
        reason=request.reason,
    )
    restored = support_case.model_copy(
        update={
            "archived_at": None,
            "archived_by": None,
            "archive_reason": None,
            "archive_history": [*support_case.archive_history, event],
            "updated_at": now,
        }
    )
    return repository.save(restored)
