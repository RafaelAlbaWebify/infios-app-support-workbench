from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.authorization_failure import evaluate_authorization_failure


def test_authorization_failure_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-authorization",
        title="Access denied after login to invoice approval",
        application="Finance Portal",
        affected_scope="one approved user",
        impact="invoice approval blocked",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-403",
            case_id=support_case.case_id,
            evidence_type="http_observation",
            source="Sanitized browser network result",
            content="Login succeeds, then POST /invoices/approve returns HTTP 403 at 10:15 UTC with correlation ID sample-403.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-role",
            case_id=support_case.case_id,
            evidence_type="role_context",
            source="Approved read-only entitlement view",
            content="The affected account is expected to have the invoice-approver role.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-repro",
            case_id=support_case.case_id,
            evidence_type="reproduction_result",
            source="Consenting affected user",
            content="The same authenticated operation was reproduced without changing access.",
            certainty=CertaintyLevel.REPRODUCED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-authorization",
            case_id=support_case.case_id,
            statement="An authenticated request to the invoice approval operation returned HTTP 403.",
            category="authorization",
            evidence_ids=["evidence-403", "evidence-repro"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_authorization_failure(support_case, evidence, observations)

    assert result.playbook_id == "authorization-failure"
    assert result.title == "Authorization or access-denied failure"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-authorization"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert all("change" not in check.name.lower() for check in result.recommended_checks)
    assert any("not proof" in warning for warning in result.safety_warnings)
    assert any("Do not add users" in warning for warning in result.safety_warnings)
    assert any("Never request" in warning for warning in result.safety_warnings)


def test_authorization_playbook_rejects_pre_login_authentication_failure() -> None:
    support_case = SupportCase(
        case_id="case-authentication",
        title="Cannot log in to Finance Portal",
        application="Finance Portal",
        impact="authentication failed with invalid credentials",
    )

    result = evaluate_authorization_failure(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1
    assert "does not yet distinguish" in result.applicability_reasons[0]


def test_authorization_playbook_rejects_post_login_server_failure_without_access_denial() -> None:
    support_case = SupportCase(
        case_id="case-server-error",
        title="Invoice page returns HTTP 500 after login",
        application="Finance Portal",
        impact="feature unavailable",
    )

    result = evaluate_authorization_failure(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1


def test_playbook_api_declares_authorization_failure_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR  # Import application package through the same test environment.
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/authorization-failure" in route_paths
    assert "/api/cases/{case_id}/playbooks/authentication-failure" in route_paths
    assert "/api/cases/{case_id}/playbooks/post-login-feature-failure" in route_paths
