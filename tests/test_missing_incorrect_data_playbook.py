from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.missing_incorrect_data import evaluate_missing_incorrect_data


def test_missing_incorrect_data_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-data",
        title="Customer record shows stale and incorrect data",
        application="Order Management",
        affected_scope="several records",
        impact="operators cannot confirm order status",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-data",
            case_id=support_case.case_id,
            evidence_type="record_comparison",
            source="Sanitized read-only comparison",
            content="Source status is SHIPPED while the application still displays PENDING for sample record at 10:15 UTC.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-repro",
            case_id=support_case.case_id,
            evidence_type="reproduction_result",
            source="Approved read-only reproduction",
            content="The same sanitized record remained stale after reopening the read-only view.",
            certainty=CertaintyLevel.REPRODUCED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-data",
            case_id=support_case.case_id,
            statement="The source and displayed statuses differ for the sanitized record.",
            category="data",
            evidence_ids=["evidence-data", "evidence-repro"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_missing_incorrect_data(support_case, evidence, observations)

    assert result.playbook_id == "missing-incorrect-data"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-data"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("Do not expose" in warning for warning in result.safety_warnings)
    assert any("Do not edit" in warning for warning in result.safety_warnings)


def test_missing_incorrect_data_playbook_defers_file_transfer_failure() -> None:
    support_case = SupportCase(case_id="case-file", title="File import failed and data is missing", application="Order Management")

    result = evaluate_missing_incorrect_data(support_case, [], [])

    assert result.applicable is False
    assert "file transfer/import/export" in result.applicability_reasons[0]


def test_missing_incorrect_data_playbook_distinguishes_api_contract_failure() -> None:
    support_case = SupportCase(case_id="case-payload", title="API schema validation invalid payload", application="Order Management")

    result = evaluate_missing_incorrect_data(support_case, [], [])

    assert result.applicable is False
    assert "API/integration" in result.applicability_reasons[0]


def test_missing_incorrect_data_playbook_lists_missing_evidence_without_claiming_root_cause() -> None:
    support_case = SupportCase(case_id="case-missing", title="Record missing from application", application="Order Management")

    result = evaluate_missing_incorrect_data(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("source" in item.lower() for item in result.missing_evidence)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_missing_incorrect_data_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/missing-incorrect-data" in route_paths
