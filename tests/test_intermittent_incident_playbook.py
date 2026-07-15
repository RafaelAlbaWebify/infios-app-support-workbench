from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.intermittent_incident import evaluate_intermittent_incident


def test_intermittent_playbook_is_applicable_and_sampling_safe() -> None:
    support_case = SupportCase(
        case_id="case-intermittent",
        title="Order submission sometimes fails",
        application="Order Service",
        affected_scope="sporadic users",
        impact="occasional blocked orders",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-occurrence",
            case_id=support_case.case_id,
            evidence_type="occurrence_log",
            source="Sanitized occurrence timeline",
            content="Success at 10:10 UTC and failure at 10:12 UTC with correlation ID intermittent-sample.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-sample",
            case_id=support_case.case_id,
            evidence_type="bounded_measurement",
            source="Approved bounded sample",
            content="One failure in five existing transactions; no additional load generated.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-intermittent",
            case_id=support_case.case_id,
            statement="Matched evidence contains both successful and failed occurrences.",
            category="intermittent",
            evidence_ids=["evidence-occurrence", "evidence-sample"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_intermittent_incident(support_case, evidence, observations)

    assert result.playbook_id == "intermittent-incident"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-intermittent"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("uncontrolled retries" in warning for warning in result.safety_warnings)
    assert any("explicit operator confirmation" in warning for warning in result.safety_warnings)


def test_intermittent_playbook_is_not_applicable_without_pattern_signal() -> None:
    support_case = SupportCase(case_id="case-stable", title="Application consistently unavailable", application="Portal")

    result = evaluate_intermittent_incident(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1


def test_intermittent_playbook_lists_missing_evidence_without_claiming_randomness() -> None:
    support_case = SupportCase(case_id="case-sporadic", title="Sporadic failure", application="Gateway")

    result = evaluate_intermittent_incident(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("bounded sample" in item.lower() for item in result.missing_evidence)
    assert any("does not mean random" in warning for warning in result.safety_warnings)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_intermittent_incident_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/intermittent-incident" in route_paths
