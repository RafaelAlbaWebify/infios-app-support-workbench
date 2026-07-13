import pytest
from pydantic import ValidationError

from app.domain import (
    ActionSafetyLevel,
    ActionStatus,
    CertaintyLevel,
    DiagnosticAction,
    EvidenceItem,
    ExplanationStatus,
    Observation,
    PossibleExplanation,
    SupportCase,
)


def test_support_case_allows_unknown_operational_details() -> None:
    case = SupportCase(title="Orders page fails after login", application="Order Management")

    assert case.case_id.startswith("case-")
    assert case.environment == "unknown"
    assert case.affected_scope == "unknown"


def test_reported_evidence_stays_reported() -> None:
    evidence = EvidenceItem(
        case_id="case-001",
        evidence_type="user_report",
        source="service desk ticket",
        content="The issue started after the deployment.",
        certainty=CertaintyLevel.REPORTED,
    )

    assert evidence.certainty is CertaintyLevel.REPORTED


def test_observation_requires_evidence_reference() -> None:
    with pytest.raises(ValidationError, match="evidence_ids"):
        Observation(
            case_id="case-001",
            statement="HTTP 500 was observed on /api/orders.",
            category="http",
            evidence_ids=[],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )


def test_explanation_cannot_be_confirmed_by_classification_alone() -> None:
    with pytest.raises(ValidationError, match="operator confirmation"):
        PossibleExplanation(
            case_id="case-001",
            statement="The deployment introduced the failure.",
            status=ExplanationStatus.CONFIRMED,
            supporting_observation_ids=["observation-001"],
            confirmed_by_operator=False,
        )


def test_confirmed_explanation_requires_supporting_observation() -> None:
    with pytest.raises(ValidationError, match="supporting observations"):
        PossibleExplanation(
            case_id="case-001",
            statement="The deployment introduced the failure.",
            status=ExplanationStatus.CONFIRMED,
            supporting_observation_ids=[],
            confirmed_by_operator=True,
        )


def test_write_or_restart_action_cannot_be_l1_safe() -> None:
    with pytest.raises(ValidationError, match="cannot be classified as L1-safe"):
        DiagnosticAction(
            case_id="case-001",
            name="Restart production application service",
            purpose="Attempt service recovery",
            safety_level=ActionSafetyLevel.L1_SAFE,
            requires_write_or_restart=True,
        )


def test_completed_action_requires_actual_result() -> None:
    with pytest.raises(ValidationError, match="actual result"):
        DiagnosticAction(
            case_id="case-001",
            name="Compare with another user",
            purpose="Determine whether the incident is user-specific",
            safety_level=ActionSafetyLevel.L1_SAFE,
            status=ActionStatus.COMPLETED,
        )


def test_completed_safe_action_preserves_result() -> None:
    action = DiagnosticAction(
        case_id="case-001",
        name="Compare with another user",
        purpose="Determine whether the incident is user-specific",
        safety_level=ActionSafetyLevel.L1_SAFE,
        status=ActionStatus.COMPLETED,
        actual_result="The second user received the same HTTP 500 error.",
        conclusion="The issue is less likely to be isolated to one user.",
        evidence_ids=["evidence-002"],
    )

    assert action.actual_result.startswith("The second user")
    assert action.conclusion is not None
