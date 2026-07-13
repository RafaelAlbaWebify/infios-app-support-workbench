from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.api.evidence import get_evidence_repository
from app.domain.models import CertaintyLevel, Observation
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository


router = APIRouter(prefix="/api/cases/{case_id}/observations", tags=["observations"])


class CreateObservationRequest(BaseModel):
    statement: str = Field(min_length=1)
    category: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    certainty: CertaintyLevel


class ObservationListResponse(BaseModel):
    observations: list[Observation]
    count: int


@lru_cache(maxsize=1)
def get_observation_repository() -> SQLiteObservationRepository:
    return SQLiteObservationRepository(DEFAULT_CASE_DATABASE)


def _require_case(case_id: str, repository: SQLiteCaseRepository) -> None:
    if repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")


def _validate_evidence_references(
    case_id: str,
    evidence_ids: list[str],
    repository: SQLiteEvidenceRepository,
) -> None:
    missing_or_wrong_case: list[str] = []
    for evidence_id in dict.fromkeys(evidence_ids):
        evidence = repository.get(evidence_id)
        if evidence is None or evidence.case_id != case_id:
            missing_or_wrong_case.append(evidence_id)

    if missing_or_wrong_case:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Every observation must reference evidence from the same case.",
                "invalid_evidence_ids": missing_or_wrong_case,
            },
        )


@router.post("", response_model=Observation, status_code=status.HTTP_201_CREATED)
def create_observation(
    case_id: str,
    request: CreateObservationRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(
        get_observation_repository
    ),
) -> Observation:
    _require_case(case_id, case_repository)
    _validate_evidence_references(case_id, request.evidence_ids, evidence_repository)

    observation = Observation(
        case_id=case_id,
        statement=request.statement,
        category=request.category,
        evidence_ids=list(dict.fromkeys(request.evidence_ids)),
        certainty=request.certainty,
    )
    return observation_repository.save(observation)


@router.get("", response_model=ObservationListResponse)
def list_observations(
    case_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    observation_repository: SQLiteObservationRepository = Depends(
        get_observation_repository
    ),
) -> ObservationListResponse:
    _require_case(case_id, case_repository)
    observations = observation_repository.list_for_case(case_id, limit=limit)
    return ObservationListResponse(
        observations=observations,
        count=len(observations),
    )


@router.get("/{observation_id}", response_model=Observation)
def get_observation(
    case_id: str,
    observation_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    observation_repository: SQLiteObservationRepository = Depends(
        get_observation_repository
    ),
) -> Observation:
    _require_case(case_id, case_repository)
    observation = observation_repository.get(observation_id)
    if observation is None or observation.case_id != case_id:
        raise HTTPException(status_code=404, detail="Observation not found")
    return observation
