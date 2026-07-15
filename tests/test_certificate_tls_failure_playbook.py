from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.certificate_tls_failure import evaluate_certificate_tls_failure


def test_certificate_tls_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-tls",
        title="TLS handshake fails with certificate hostname mismatch",
        application="Partner Gateway",
        affected_scope="multiple clients",
        impact="integration blocked",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-tls",
            case_id=support_case.case_id,
            evidence_type="tls_error",
            source="Sanitized client log",
            content="Certificate verify failed: hostname mismatch at 10:15 UTC.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-cert",
            case_id=support_case.case_id,
            evidence_type="certificate_metadata",
            source="Approved certificate viewer",
            content="SAN contains gateway.example.test; no private key material captured.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-tls",
            case_id=support_case.case_id,
            statement="The approved client reproduced a hostname validation failure.",
            category="tls",
            evidence_ids=["evidence-tls", "evidence-cert"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_certificate_tls_failure(support_case, evidence, observations)

    assert result.playbook_id == "certificate-tls-failure"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-tls"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("private keys" in warning for warning in result.safety_warnings)
    assert any("Do not bypass" in warning for warning in result.safety_warnings)


def test_certificate_tls_playbook_does_not_absorb_access_failure() -> None:
    support_case = SupportCase(case_id="case-access", title="Access denied due to invalid credentials", application="Portal")

    result = evaluate_certificate_tls_failure(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1


def test_certificate_tls_playbook_lists_missing_evidence_without_claiming_root_cause() -> None:
    support_case = SupportCase(case_id="case-expired", title="Certificate expired", application="Gateway")

    result = evaluate_certificate_tls_failure(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("certificate metadata" in item.lower() for item in result.missing_evidence)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_certificate_tls_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/certificate-tls-failure" in route_paths
