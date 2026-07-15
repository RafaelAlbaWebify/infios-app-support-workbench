from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ServiceKind(str, Enum):
    APPLICATION = "application"
    API = "api"
    DATABASE = "database"
    QUEUE = "queue"
    SCHEDULER = "scheduler"
    FILE_TRANSFER = "file_transfer"
    IDENTITY = "identity"
    EXTERNAL_PROVIDER = "external_provider"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


class Criticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class DependencyType(str, Enum):
    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    DATA = "data"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    OPERATIONAL = "operational"
    OTHER = "other"


class ServiceCatalogueEntry(BaseModel):
    service_id: str = Field(default_factory=lambda: _new_id("service"))
    name: str = Field(min_length=1, max_length=200)
    kind: ServiceKind
    description: str | None = Field(default=None, max_length=2000)
    owner_team: str | None = Field(default=None, max_length=200)
    support_contact: str | None = Field(default=None, max_length=300)
    criticality: Criticality = Criticality.UNKNOWN
    environments: list[str] = Field(default_factory=list, max_length=20)
    runbook_reference: str | None = Field(default=None, max_length=500)
    status_page_reference: str | None = Field(default=None, max_length=500)
    active: bool = True
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ServiceDependency(BaseModel):
    dependency_id: str = Field(default_factory=lambda: _new_id("dependency"))
    source_service_id: str = Field(min_length=1)
    target_service_id: str = Field(min_length=1)
    dependency_type: DependencyType
    required: bool = True
    description: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def prevent_self_dependency(self) -> ServiceDependency:
        if self.source_service_id == self.target_service_id:
            raise ValueError("A service cannot depend on itself.")
        return self
