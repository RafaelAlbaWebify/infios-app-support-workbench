from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.service_unavailable import evaluate_service_unavailable


def test_service_unavailable_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-availability",
        title="Order API returns 503 Service Unavailable",
        application="Order Management",
        affected_scope="multiple users and locations",
        impact="critical order processing blocked",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-http",
            case_id=support_case.case_id,
            evidence_type="http_observation",
            source="Sanitized browser response",
            content="HTTP 503 Service Unavailable from the approved order endpoint at 10:15 UTC with correlation ID sample-503.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-repro",
            case_id=support_case.case_id,
            evidence_type="reproduction_result",
            source="Approved read-only reproduction",
            content="The same request returned 503 from two approved clients without changing the service.",
            certainty=CertaintyLevel.REPRODUCED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-availability",
            case_id=support_case.case_id,
            statement="The approved order request reproduced HTTP 503 during the reported time window.",
            category="availability",
            evidence_ids=["evidence-http", "evidence-repro"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_service_unavailable(support_case, evidence, observations)

    assert result.playbook_id == "service-unavailable"
    assert result.title == "Service unavailable or gateway failure"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-availability"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("does not by itself prove" in warning for warning in result.safety_warnings)
    assert any("Do not restart" in warning for warning in result.safety_warnings)
    assert any("bounded" in warning for warning in result.safety_warnings)


def test_service_unavailable_playbook_rejects_authentication_or_authorization_symptoms() -> None:
    authentication_case = SupportCase(
        case_id="case-auth",
        title="Cannot log in because authentication failed",
        application="Order Management",
    )
    authorization_case = SupportCase(
        case_id="case-authz",
        title="Authenticated user receives HTTP 403 Forbidden",
        application="Order Management",
    )

    authentication_result = evaluate_service_unavailable(authentication_case, [], [])
    authorization_result = evaluate_service_unavailable(authorization_case, [], [])

    assert authentication_result.applicable is False
    assert authorization_result.applicable is False
    assert len(authentication_result.recommended_checks) == 1
    assert len(authorization_result.recommended_checks) == 1


def test_service_unavailable_playbook_distinguishes_direct_application_500() -> None:
    support_case = SupportCase(
        case_id="case-500",
        title="Application returns 500 Internal Server Error with an unhandled exception",
        application="Order Management",
    )

    result = evaluate_service_unavailable(support_case, [], [])

    assert result.applicable is False
    assert "application-side failure" in result.applicability_reasons[0]


def test_service_unavailable_playbook_lists_missing_evidence_without_claiming_root_cause() -> None:
    support_case = SupportCase(
        case_id="case-502",
        title="HTTP 502 Bad Gateway",
        application="Order Management",
    )

    result = evaluate_service_unavailable(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("health" in item.lower() for item in result.missing_evidence)
    assert any("gateway" in explanation.lower() for explanation in result.possible_explanations)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_service_unavailable_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/service-unavailable" in route_paths
