from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.observations import get_observation_repository
from app.domain.models import CertaintyLevel, TimelineEvent, TimestampPrecision
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository

router = APIRouter(prefix="/api/cases/{case_id}/timeline", tags=["timeline"])


class TimelineResponse(BaseModel):
    events: list[TimelineEvent]
    count: int


def _event_time(value: datetime | None) -> datetime:
    return value or datetime.max.replace(tzinfo=timezone.utc)


@router.get("", response_model=TimelineResponse)
def get_timeline(
    case_id: str,
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
    observation_repository: SQLiteObservationRepository = Depends(get_observation_repository),
    action_repository: SQLiteActionRepository = Depends(get_action_repository),
) -> TimelineResponse:
    support_case = case_repository.get(case_id)
    if support_case is None:
        raise HTTPException(status_code=404, detail="Support case not found")

    events: list[TimelineEvent] = [
        TimelineEvent(
            case_id=case_id,
            timestamp=support_case.created_at,
            timestamp_precision=TimestampPrecision.EXACT,
            event_type="case_created",
            summary=f"Case created: {support_case.title}",
            source_reference=support_case.case_id,
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    for evidence in evidence_repository.list_for_case(case_id, limit=500):
        events.append(
            TimelineEvent(
                case_id=case_id,
                timestamp=evidence.observed_at or evidence.collected_at,
                timestamp_precision=(
                    TimestampPrecision.EXACT if evidence.observed_at else TimestampPrecision.APPROXIMATE
                ),
                event_type="evidence",
                summary=f"Evidence added: {evidence.evidence_type}",
                source_reference=evidence.evidence_id,
                certainty=evidence.certainty,
            )
        )

    for observation in observation_repository.list_for_case(case_id, limit=500):
        events.append(
            TimelineEvent(
                case_id=case_id,
                timestamp=observation.created_at,
                timestamp_precision=TimestampPrecision.EXACT,
                event_type="observation",
                summary=observation.statement,
                source_reference=observation.observation_id,
                certainty=observation.certainty,
            )
        )

    for action in action_repository.list_for_case(case_id, limit=500):
        if action.started_at:
            events.append(
                TimelineEvent(
                    case_id=case_id,
                    timestamp=action.started_at,
                    timestamp_precision=TimestampPrecision.EXACT,
                    event_type="action_started",
                    summary=f"Diagnostic action started: {action.name}",
                    source_reference=action.action_id,
                    certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
                )
            )
        if action.completed_at:
            events.append(
                TimelineEvent(
                    case_id=case_id,
                    timestamp=action.completed_at,
                    timestamp_precision=TimestampPrecision.EXACT,
                    event_type="action_completed",
                    summary=f"Diagnostic action completed: {action.name}",
                    source_reference=action.action_id,
                    certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
                )
            )

    events.sort(key=lambda event: (_event_time(event.timestamp), event.event_type, event.event_id))
    return TimelineResponse(events=events, count=len(events))
