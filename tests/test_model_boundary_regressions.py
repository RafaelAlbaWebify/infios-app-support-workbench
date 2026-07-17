import pytest
from pydantic import ValidationError

from app.domain.models import (
    ActionSafetyLevel,
    ActionStatus,
    DiagnosticAction,
    ExplanationStatus,
    PossibleExplanation,
)
from app.known_error_models import KnownErrorRecord, WorkaroundSafety


def test_change_action_cannot_use_safe_classification() -> None:
    with pytest.raises(ValidationError, match="cannot be classified as L1-safe"):
        DiagnosticAction(
            case_id="case-boundary",
            name="Service operation",
            purpose="Restore availability",
            safety_level=ActionSafetyLevel.L1_SAFE,
            requires_write_or_restart=True,
        )


def test_completed_action_requires_result() -> None:
    with pytest.raises(ValidationError, match="requires an actual result"):
        DiagnosticAction(
            case_id="case-boundary",
            name="Inspect health endpoint",
            purpose="Collect current state",
            safety_level=ActionSafetyLevel.L1_SAFE,
            status=ActionStatus.COMPLETED,
        )


def test_change_guidance_cannot_use_read_only_classification() -> None:
    with pytest.raises(ValidationError, match="cannot be classified as read-only"):
        KnownErrorRecord(
            problem_id="problem-boundary",
            title="Operational workaround",
            symptom_summary="Requests remain pending.",
            workaround_steps=["Perform the documented operation."],
            workaround_limitations="Requires an approved change.",
            validation_guidance="Confirm requests resume and attach evidence.",
            safety=WorkaroundSafety.READ_ONLY,
            requires_write_or_restart=True,
            owner="Application Support",
            created_by="L2 Support",
        )


def test_confirmed_explanation_requires_explicit_support() -> None:
    with pytest.raises(ValidationError, match="explicit operator confirmation"):
        PossibleExplanation(
            case_id="case-boundary",
            statement="A dependency interruption caused the failure.",
            status=ExplanationStatus.CONFIRMED,
            supporting_observation_ids=["observation-1"],
        )

    with pytest.raises(ValidationError, match="supporting observations"):
        PossibleExplanation(
            case_id="case-boundary",
            statement="A dependency interruption caused the failure.",
            status=ExplanationStatus.CONFIRMED,
            confirmed_by_operator=True,
        )
