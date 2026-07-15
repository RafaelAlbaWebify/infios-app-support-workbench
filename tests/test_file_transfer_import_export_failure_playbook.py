from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.file_transfer_import_export_failure import evaluate_file_transfer_import_export_failure


def test_file_transfer_playbook_is_applicable_and_safe() -> None:
    support_case = SupportCase(
        case_id="case-file",
        title="Inbound SFTP file rejected after transfer",
        application="Order Management",
        affected_scope="one partner feed",
        impact="orders not imported",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-file",
            case_id=support_case.case_id,
            evidence_type="transfer_status",
            source="Sanitized transfer history",
            content="Inbound file sample.csv landed at 10:15 UTC and validation rejected it with checksum mismatch.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        )
    ]
    observations = [
        Observation(
            observation_id="observation-file",
            case_id=support_case.case_id,
            statement="The file landed but validation rejected it before import.",
            category="file_transfer",
            evidence_ids=["evidence-file"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_file_transfer_import_export_failure(support_case, evidence, observations)

    assert result.playbook_id == "file-transfer-import-export-failure"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-file"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("Do not retransmit" in warning for warning in result.safety_warnings)
    assert any("Never collect passwords" in warning for warning in result.safety_warnings)


def test_file_transfer_playbook_defers_access_failure() -> None:
    support_case = SupportCase(
        case_id="case-access",
        title="SFTP authentication failed due to invalid credentials",
        application="Order Management",
    )

    result = evaluate_file_transfer_import_export_failure(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1


def test_file_transfer_playbook_lists_missing_evidence() -> None:
    support_case = SupportCase(case_id="case-export", title="Export file not delivered", application="Order Management")

    result = evaluate_file_transfer_import_export_failure(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("checksum" in item.lower() for item in result.missing_evidence)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_file_transfer_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/file-transfer-import-export-failure" in route_paths
