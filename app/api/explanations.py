from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError

from app.api.actions import get_action_repository
from app.api.cases import DEFAULT_CASE_DATABASE, get_case_repository
from app.api.observations import get_observation_repository
from app.domain.models import ExplanationStatus, PossibleExplanation
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_explanation_repository import SQLiteExplanationRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository


router = APIRouter(prefix="/api/cases/{case_id}/explanations", tags=["explanations"])


class CreateExplanationRequest(BaseModel):
    statement: str = Field(min_length=1)
    supporting_observation_ids: list[str] = Field(default_factory=list)
    contradicting_observation_ids: list[str] = Field(default_factory=list)
    validation_action_ids: list[str] = Field(default_factory=list)


class UpdateExplanationStatusRequest(BaseModel):
    status: ExplanationStatus
    confirmed_by_operator: bool = False


class ExplanationListResponse(BaseModel):
    explanations: list[PossibleExplanation]
    count: int


@lru_cache(maxsize=1)
def get_explanation_repository() -> SQLiteExplanationRepository:
    return SQLiteExplanationRepository(DEFAULT_CASE_DATABASE)


def _require_case(case_id: str, repository: SQLiteCaseRepository) -> None:
    if repository.get(case_id) is None:
        raise HTTPException(status_code=404, detail="Support case not found")


def _validate_observation_ids(
    case_id: str,
    observation_ids: list[str],
    repository: SQLiteObservationRepository,
) -> list[str]:
    normalized = list(dict.fromkeys(observation_ids))
    invalid = []
    for observation_id in normalized:
        observation = repository.get(observation_id)
        if observation is None or observation.case_id != case_id:
            invalid.append(observation_id)
    if invalid:
        raise HTTPException(
            status_code=422,
            detail={"invalid_observation_ids": invalid},
        )
    return normalized


def _validate_action_ids(
    case_id: str,
    action_ids: list[str],
    repository: SQLiteActionRepository,
) -> list[str]:
    normalized = list(dict.fromkeys(action_ids))
    invalid = []
    for action_id in normalized:
        action = repository.get(action_id)
        if action is None or action.case_id != case_id:
            invalid.append(action_id)
    if invalid:
        raise HTTPException(status_code=422, detail={"invalid_action_ids": invalid})
    return normalized


@router.post("", response_model=PossibleExplanation, status_code=status.HTTP_201_CREATED)
def create_explanation(
    case_id: str,
    request: CreateExplanationRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
    explanation_repository: SQLiteExplanationRepository = Depends(get_explanation_repository),
) -> PossibleExplanation:
    _require_case(case_id, case_repository)
    supporting = _validate_observation_ids(
        case_id, request.supporting_observation_ids, observation_repository
    )
    contradicting = _validate_observation_ids(
        case_id, request.contradicting_observation_ids, observation_repository
    )
    actions = _validate_action_ids(case_id, request.validation_action_ids, action_repository)
    explanation = PossibleExplanation(
        case_id=case_id,
        statement=request.statement,
        supporting_observation_ids=supporting,
        contradicting_observation_ids=contradicting,
        validation_action_ids=actions,
    )
    return explanation_repository.save(explanation)


@router.get("", response_model=ExplanationListResponse)
def list_explanations(
    case_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    explanation_repository: SQLiteExplanationRepository = Depends(get_explanation_repository),
) -> ExplanationListResponse:
    _require_case(case_id, case_repository)
    explanations = explanation_repository.list_for_case(case_id, limit=limit)
    return ExplanationListResponse(explanations=explanations, count=len(explanations))


@router.get("/{explanation_id}", response_model=PossibleExplanation)
def get_explanation(
    case_id: str,
    explanation_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    explanation_repository: SQLiteExplanationRepository = Depends(get_explanation_repository),
) -> PossibleExplanation:
    _require_case(case_id, case_repository)
    explanation = explanation_repository.get(explanation_id)
    if explanation is None or explanation.case_id != case_id:
        raise HTTPException(status_code=404, detail="Possible explanation not found")
    return explanation


@router.post("/{explanation_id}/status", response_model=PossibleExplanation)
def update_explanation_status(
    case_id: str,
    explanation_id: str,
    request: UpdateExplanationStatusRequest,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    explanation_repository: SQLiteExplanationRepository = Depends(get_explanation_repository),
) -> PossibleExplanation:
    _require_case(case_id, case_repository)
    explanation = explanation_repository.get(explanation_id)
    if explanation is None or explanation.case_id != case_id:
        raise HTTPException(status_code=404, detail="Possible explanation not found")
    try:
        updated = PossibleExplanation.model_validate(
            {
                **explanation.model_dump(),
                "status": request.status,
                "confirmed_by_operator": request.confirmed_by_operator,
            }
        )
    except ValidationError as exc:
        message = "; ".join(error["msg"] for error in exc.errors())
        raise HTTPException(status_code=422, detail=message) from exc
    return explanation_repository.save(updated)
