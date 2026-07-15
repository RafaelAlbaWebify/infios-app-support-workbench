from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.performance_degradation import evaluate_performance_degradation


def test_performance_degradation_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-performance",
        title="Order search is slow and takes 18 seconds",
        application="Order Management",
        affected_scope="multiple users",
        impact="order handling delayed",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-timing",
            case_id=support_case.case_id,
            evidence_type="performance_measurement",
            source="Approved timing observation",
            content="Order search completed in 18.2 seconds at 10:15 UTC; known-good baseline is 2.1 seconds.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-repro",
            case_id=support_case.case_id,
            evidence_type="reproduction_result",
            source="Approved read-only reproduction",
            content="Three bounded attempts reproduced high latency without generating additional load.",
            certainty=CertaintyLevel.REPRODUCED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-performance",
            case_id=support_case.case_id,
            statement="The approved order search remained available but exceeded the known-good response-time baseline.",
            category="performance",
            evidence_ids=["evidence-timing", "evidence-repro"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_performance_degradation(support_case, evidence, observations)

    assert result.playbook_id == "performance-degradation"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-performance"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("load-test" in warning for warning in result.safety_warnings)
    assert any("Do not clear caches" in warning for warning in result.safety_warnings)
    assert any("does not by itself prove" in warning for warning in result.safety_warnings)


def test_performance_playbook_rejects_hard_unavailability_and_access_failures() -> None:
    unavailable_case = SupportCase(case_id="case-503", title="HTTP 503 Service Unavailable", application="Orders")
    access_case = SupportCase(case_id="case-403", title="HTTP 403 Forbidden", application="Orders")

    assert evaluate_performance_degradation(unavailable_case, [], []).applicable is False
    assert evaluate_performance_degradation(access_case, [], []).applicable is False


def test_performance_playbook_lists_missing_evidence_and_preserves_uncertainty() -> None:
    support_case = SupportCase(case_id="case-slow", title="Application is very slow", application="Orders")

    result = evaluate_performance_degradation(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("baseline" in item.lower() for item in result.missing_evidence)
    assert any("may" in explanation.lower() for explanation in result.possible_explanations)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_performance_degradation_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/performance-degradation" in route_paths
