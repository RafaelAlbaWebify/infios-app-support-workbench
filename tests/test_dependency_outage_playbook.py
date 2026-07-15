from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.dependency_outage import evaluate_dependency_outage


def test_dependency_outage_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-dependency",
        title="Upstream dependency unavailable",
        application="Order Service",
        affected_scope="multiple users",
        impact="order submission blocked",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-dependency",
            case_id=support_case.case_id,
            evidence_type="dependency_error",
            source="Sanitized application trace",
            content="Upstream unavailable at 10:15 UTC with correlation ID dep-sample.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-status",
            case_id=support_case.case_id,
            evidence_type="dependency_status",
            source="Approved dependency dashboard",
            content="Dependency health check failed in the affected region.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-dependency",
            case_id=support_case.case_id,
            statement="The application trace and approved health view show the same dependency boundary failure.",
            category="dependency",
            evidence_ids=["evidence-dependency", "evidence-status"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_dependency_outage(support_case, evidence, observations)

    assert result.playbook_id == "dependency-outage"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-dependency"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("force failover" in warning for warning in result.safety_warnings)
    assert any("duplicate transactions" in warning for warning in result.safety_warnings)


def test_dependency_outage_playbook_does_not_absorb_direct_feature_bug() -> None:
    support_case = SupportCase(case_id="case-feature", title="Local validation error in feature bug", application="Portal")

    result = evaluate_dependency_outage(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1


def test_dependency_outage_playbook_lists_missing_evidence_without_claiming_root_cause() -> None:
    support_case = SupportCase(case_id="case-provider", title="Vendor outage", application="Gateway")

    result = evaluate_dependency_outage(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("correlation trace" in item.lower() for item in result.missing_evidence)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_dependency_outage_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/dependency-outage" in route_paths
