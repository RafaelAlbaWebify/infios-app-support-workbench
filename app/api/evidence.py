from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.correlation_extraction import extract_correlation_identifiers
from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity
from app.log_ingestion import sanitize_log_text
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


router = APIRouter(prefix="/api/cases/{case_id}/evidence", tags=["evidence"])


class CreateEvidenceRequest(BaseModel):
    evidence_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    content: str | dict[str, Any]
    observed_at: datetime | None = None
    certainty: CertaintyLevel = CertaintyLevel.UNKNOWN
    sensitivity: EvidenceSensitivity = EvidenceSensitivity.INTERNAL
    redacted: bool = False
    attachment_reference: str | None = None
    notes: str | None = None


class ImportLogRequest(BaseModel):
    source: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    observed_at: datetime | None = None
    certainty: CertaintyLevel = CertaintyLevel.UNKNOWN
    sensitivity: EvidenceSensitivity = EvidenceSensitivity.INTERNAL


class CorrelationIdentifierResponse(BaseModel):
    kind: str
    value: str


class ImportedLogResponse(BaseModel):
    evidence: EvidenceItem
    original_bytes: int
    line_count: int
    redactions: dict[str, int]
    correlation_identifiers: list[CorrelationIdentifierResponse]


class EvidenceListResponse(BaseModel):
    evidence: list[EvidenceItem]
    count: int


@lru_cache(maxsize=1)
def get_evidence_repository() -> SQLiteEvidenceRepository:
    return SQLiteEvidenceRepository(DEFAULT_CASE_DATABASE)


def _require_case(case_id: str, repository: SQLiteCaseRepository) -> None:
    if repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")


@router.post("", response_model=EvidenceItem, status_code=status.HTTP_201_CREATED)
def create_evidence(
    case_id: str,
    request: CreateEvidenceRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
) -> EvidenceItem:
    _require_case(case_id, case_repository)
    evidence = EvidenceItem(
        case_id=case_id,
        evidence_type=request.evidence_type,
        source=request.source,
        observed_at=request.observed_at,
        content=request.content,
        certainty=request.certainty,
        sensitivity=request.sensitivity,
        redacted=request.redacted,
        attachment_reference=request.attachment_reference,
        notes=request.notes,
    )
    return evidence_repository.save(evidence)


@router.post("/import-log", response_model=ImportedLogResponse, status_code=status.HTTP_201_CREATED)
def import_sanitized_log(
    case_id: str,
    request: ImportLogRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
) -> ImportedLogResponse:
    _require_case(case_id, case_repository)
    try:
        result = sanitize_log_text(request.content)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    identifiers = extract_correlation_identifiers(result.content)
    redactions = {finding.kind: finding.replacements for finding in result.findings}
    evidence = EvidenceItem(
        case_id=case_id,
        evidence_type="log_sample",
        source=request.source,
        observed_at=request.observed_at,
        content=result.content,
        certainty=request.certainty,
        sensitivity=request.sensitivity,
        redacted=True,
        notes=(
            f"Sanitized log import: {result.line_count} line(s), {result.original_bytes} original byte(s), "
            f"{sum(redactions.values())} automatic redaction(s), {len(identifiers)} correlation identifier(s)."
        ),
    )
    saved = evidence_repository.save(evidence)
    return ImportedLogResponse(
        evidence=saved,
        original_bytes=result.original_bytes,
        line_count=result.line_count,
        redactions=redactions,
        correlation_identifiers=[
            CorrelationIdentifierResponse(kind=identifier.kind, value=identifier.value)
            for identifier in identifiers
        ],
    )


@router.get("", response_model=EvidenceListResponse)
def list_evidence(
    case_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
) -> EvidenceListResponse:
    _require_case(case_id, case_repository)
    evidence = evidence_repository.list_for_case(case_id, limit=limit)
    return EvidenceListResponse(evidence=evidence, count=len(evidence))


@router.get("/{evidence_id}", response_model=EvidenceItem)
def get_evidence(
    case_id: str,
    evidence_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
) -> EvidenceItem:
    _require_case(case_id, case_repository)
    evidence = evidence_repository.get(evidence_id)
    if evidence is None or evidence.case_id != case_id:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    return evidence
