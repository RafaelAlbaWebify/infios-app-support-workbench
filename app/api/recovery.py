from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError

from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.api.evidence import get_evidence_repository
from app.domain.recovery import RecoveryOutcome, RecoveryValidation
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_recovery_repository import SQLiteRecoveryRepository


router = APIRouter(prefix="/api/cases/{case_id}/recovery-validations", tags=["recovery"])


class CreateRecoveryValidationRequest(BaseModel):
    outcome: RecoveryOutcome
    method: str = Field(min_length=1)
    result: str = Field(min_length=1)
    performed_by: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class RecoveryValidationListResponse(BaseModel):
    validations: list[RecoveryValidation]
    count: int


@lru_cache(maxsize=1)
def get_recovery_repository() -> SQLiteRecoveryRepository:
    return SQLiteRecoveryRepository(DEFAULT_CASE_DATABASE)


def _require_case(case_id: str, repository: SQLiteCaseRepository) -> None:
    if repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")


def _validate_evidence_ids(
    case_id: str,
    evidence_ids: list[str],
    repository: SQLiteEvidenceRepository,
) -> list[str]:
    normalized = list(dict.fromkeys(evidence_ids))
    invalid = []
    for evidence_id in normalized:
        evidence = repository.get(evidence_id)
        if evidence is None or evidence.case_id != case_id:
            invalid.append(evidence_id)
    if invalid:
        raise HTTPException(status_code=422, detail={"invalid_evidence_ids": invalid})
    return normalized


@router.post("", response_model=RecoveryValidation, status_code=status.HTTP_201_CREATED)
def create_recovery_validation(
    case_id: str,
    request: CreateRecoveryValidationRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    recovery_repository: SQLiteRecoveryRepository = Depends(get_recovery_repository),
) -> RecoveryValidation:
    _require_case(case_id, case_repository)
    evidence_ids = _validate_evidence_ids(case_id, request.evidence_ids, evidence_repository)
    try:
        validation = RecoveryValidation(
            case_id=case_id,
            outcome=request.outcome,
            method=request.method,
            result=request.result,
            performed_by=request.performed_by,
            evidence_ids=evidence_ids,
            notes=request.notes,
        )
    except ValidationError as exc:
        message = "; ".join(error["msg"] for error in exc.errors())
        raise HTTPException(status_code=422, detail=message) from exc
    return recovery_repository.save(validation)


@router.get("", response_model=RecoveryValidationListResponse)
def list_recovery_validations(
    case_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    recovery_repository: SQLiteRecoveryRepository = Depends(get_recovery_repository),
) -> RecoveryValidationListResponse:
    _require_case(case_id, case_repository)
    validations = recovery_repository.list_for_case(case_id, limit=limit)
    return RecoveryValidationListResponse(validations=validations, count=len(validations))


@router.get("/{validation_id}", response_model=RecoveryValidation)
def get_recovery_validation(
    case_id: str,
    validation_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    recovery_repository: SQLiteRecoveryRepository = Depends(get_recovery_repository),
) -> RecoveryValidation:
    _require_case(case_id, case_repository)
    validation = recovery_repository.get(validation_id)
    if validation is None or validation.case_id != case_id:
        raise HTTPException(status_code=404, detail="Recovery validation not found")
    return validation
