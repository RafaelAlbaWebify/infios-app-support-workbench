from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.authentication_failure import evaluate_authentication_failure


def test_authentication_failure_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-auth",
        title="Cannot log in to Order Management",
        application="Order Management",
        affected_scope="several users",
        impact="critical business process blocked",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-auth",
            case_id=support_case.case_id,
            evidence_type="authentication_result",
            source="Sanitized sign-in log",
            content="Authentication failed during MFA with correlation ID sample-123 at 10:15 UTC.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-repro",
            case_id=support_case.case_id,
            evidence_type="reproduction_result",
            source="Approved test account",
            content="Login fails before an application session is established.",
            certainty=CertaintyLevel.REPRODUCED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-auth",
            case_id=support_case.case_id,
            statement="The approved test account did not establish an authenticated session.",
            category="authentication",
            evidence_ids=["evidence-auth", "evidence-repro"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_authentication_failure(support_case, evidence, observations)

    assert result.playbook_id == "authentication-failure"
    assert result.title == "Authentication or login failure"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-auth"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("Never request" in warning for warning in result.safety_warnings)
    assert any("MFA" in explanation for explanation in result.possible_explanations)


def test_authentication_playbook_rejects_post_login_symptom_as_not_proven_authentication() -> None:
    support_case = SupportCase(
        case_id="case-post-login",
        title="Orders page returns an error after login",
        application="Order Management",
    )

    result = evaluate_authentication_failure(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1
    assert "does not yet distinguish" in result.applicability_reasons[0]


def test_playbook_api_declares_authentication_failure_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR  # Import application package through the same test environment.
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/authentication-failure" in route_paths
    assert "/api/cases/{case_id}/playbooks/post-login-feature-failure" in route_paths
