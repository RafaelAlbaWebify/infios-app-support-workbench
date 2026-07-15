from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.api_integration_failure import evaluate_api_integration_failure


def test_api_integration_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-api",
        title="Partner API rejects payload with 422 Unprocessable Entity",
        application="Order Integration",
        affected_scope="all partner submissions",
        impact="orders are not accepted",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-api",
            case_id=support_case.case_id,
            evidence_type="api_response",
            source="Sanitized integration log",
            content="HTTP 422 schema validation error for required field with correlation ID sample-api at 10:15 UTC.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-repro",
            case_id=support_case.case_id,
            evidence_type="reproduction_result",
            source="Approved non-production validation",
            content="The sanitized payload shape reproduced the same validation error in the approved test environment.",
            certainty=CertaintyLevel.REPRODUCED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-api",
            case_id=support_case.case_id,
            statement="The approved non-production validation reproduced the 422 contract rejection.",
            category="integration",
            evidence_ids=["evidence-api", "evidence-repro"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_api_integration_failure(support_case, evidence, observations)

    assert result.playbook_id == "api-integration-failure"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-api"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("Never collect" in warning for warning in result.safety_warnings)
    assert any("Do not replay" in warning for warning in result.safety_warnings)


def test_api_integration_playbook_defers_gateway_availability_failure() -> None:
    support_case = SupportCase(case_id="case-503", title="Partner API returns 503 Service Unavailable", application="Order Integration")

    result = evaluate_api_integration_failure(support_case, [], [])

    assert result.applicable is False
    assert "service-unavailable" in result.applicability_reasons[0]
    assert len(result.recommended_checks) == 1


def test_api_integration_playbook_distinguishes_access_failure() -> None:
    support_case = SupportCase(case_id="case-401", title="Partner API returns 401 invalid token", application="Order Integration")

    result = evaluate_api_integration_failure(support_case, [], [])

    assert result.applicable is False
    assert "authentication or authorization" in result.applicability_reasons[0]


def test_api_integration_playbook_lists_missing_evidence_without_claiming_root_cause() -> None:
    support_case = SupportCase(case_id="case-webhook", title="Webhook failed with invalid payload", application="Order Integration")

    result = evaluate_api_integration_failure(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("contract" in item.lower() for item in result.missing_evidence)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_api_integration_failure_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/api-integration-failure" in route_paths
