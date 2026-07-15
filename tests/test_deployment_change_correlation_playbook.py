from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.deployment_change_correlation import evaluate_deployment_change_correlation


def test_deployment_change_playbook_is_applicable_and_causality_safe() -> None:
    support_case = SupportCase(
        case_id="case-change",
        title="Failures started after deployment",
        application="Order Service",
        affected_scope="one production version",
        impact="order submission blocked",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-change",
            case_id=support_case.case_id,
            evidence_type="change_record",
            source="Approved change record",
            content="Version 2.4 deployment completed at 10:00 UTC.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-timeline",
            case_id=support_case.case_id,
            evidence_type="incident_timeline",
            source="Sanitized monitoring timeline",
            content="Last known good 09:55 UTC; first failure 10:08 UTC.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-change",
            case_id=support_case.case_id,
            statement="The first observed failure followed the recorded deployment window.",
            category="change",
            evidence_ids=["evidence-change", "evidence-timeline"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_deployment_change_correlation(support_case, evidence, observations)

    assert result.playbook_id == "deployment-change-correlation"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-change"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("context, not proof" in warning for warning in result.safety_warnings)
    assert any("explicitly confirms" in warning for warning in result.safety_warnings)


def test_deployment_change_playbook_is_not_applicable_without_change_signal() -> None:
    support_case = SupportCase(case_id="case-no-change", title="Application error", application="Portal")

    result = evaluate_deployment_change_correlation(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1


def test_deployment_change_playbook_requires_causal_validation() -> None:
    support_case = SupportCase(case_id="case-release", title="Recent release correlation", application="Gateway")

    result = evaluate_deployment_change_correlation(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("timing alone is not proof" in item.lower() for item in result.missing_evidence)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_deployment_change_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/deployment-change-correlation" in route_paths
