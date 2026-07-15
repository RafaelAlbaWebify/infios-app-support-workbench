from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.background_job_scheduler_failure import evaluate_background_job_scheduler_failure


def test_background_job_playbook_is_applicable_and_safe() -> None:
    support_case = SupportCase(
        case_id="case-job",
        title="Nightly scheduled job failed and retries exhausted",
        application="Order Management",
        affected_scope="all tenants",
        impact="daily reconciliation missing",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-job",
            case_id=support_case.case_id,
            evidence_type="job_status",
            source="Sanitized scheduler history",
            content="Job reconciliation failed at 02:00 UTC after three attempts with sample error code JOB-42.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        )
    ]
    observations = [
        Observation(
            observation_id="observation-job",
            case_id=support_case.case_id,
            statement="The expected scheduled run failed and exhausted retries.",
            category="scheduler",
            evidence_ids=["evidence-job"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_background_job_scheduler_failure(support_case, evidence, observations)

    assert result.playbook_id == "background-job-scheduler-failure"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-job"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("Do not manually trigger" in warning for warning in result.safety_warnings)
    assert any("Do not purge queues" in warning for warning in result.safety_warnings)


def test_background_job_playbook_defers_file_transfer_failure() -> None:
    support_case = SupportCase(
        case_id="case-transfer",
        title="Scheduled SFTP file transfer failed",
        application="Order Management",
    )

    result = evaluate_background_job_scheduler_failure(support_case, [], [])

    assert result.applicable is False
    assert len(result.recommended_checks) == 1


def test_background_job_playbook_lists_missing_evidence() -> None:
    support_case = SupportCase(case_id="case-missed", title="Batch job missed its schedule", application="Order Management")

    result = evaluate_background_job_scheduler_failure(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("worker" in item.lower() for item in result.missing_evidence)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_background_job_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/background-job-scheduler-failure" in route_paths
