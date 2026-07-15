from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_background_job_scheduler_failure(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    scheduler_signal = any(
        phrase in searchable
        for phrase in (
            "scheduled job", "background job", "batch job", "scheduler", "cron", "task did not run",
            "job failed", "job stuck", "job missed", "job overdue", "queue worker", "worker stopped",
            "retry exhausted", "dead letter", "processing backlog", "next run", "last run failed",
        )
    )
    file_transfer_signal = any(
        phrase in searchable for phrase in ("sftp", "ftp", "file transfer", "import file", "export file")
    )
    applicable = scheduler_signal and not file_transfer_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("job_status", "scheduler_status", "error_message", "job_log")):
        missing.append("Sanitized job status, scheduler message, or exact failure evidence")
    if not any(kind in evidence_types for kind in ("run_history", "execution_history", "reproduction_result")):
        missing.append("Run history with expected time, actual start/end, status, and attempt count")
    if not any(kind in evidence_types for kind in ("scope_comparison", "job_comparison", "working_example")):
        missing.append("Comparison with another schedule, worker, queue, environment, or successful run")
    if not any(kind in evidence_types for kind in ("dependency_status", "queue_status", "worker_status", "monitoring_snapshot")):
        missing.append("Approved read-only worker, queue, dependency, or scheduler health evidence")
    if not any(kind in evidence_types for kind in ("recent_change", "deployment", "configuration_change", "change_record")):
        missing.append("Recent schedule, worker, dependency, credential, deployment, or configuration-change context")

    checks = [
        GuidedCheck(
            check_id="capture-job-boundary",
            name="Capture the exact job execution boundary",
            purpose="Identify the expected schedule, last successful run, first failed or missed run, and current state.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only scheduler, job-history, and monitoring views.",
                "Record job identifier, expected time, actual start/end, status, attempt count, error code, and correlation identifier.",
                "Do not manually trigger, retry, cancel, or reschedule the job during diagnosis.",
            ],
            evidence_to_capture=["job identifier", "expected schedule", "last success", "first failure", "status", "attempt count", "error code"],
        ),
        GuidedCheck(
            check_id="compare-run-and-scope",
            name="Compare run history and affected scope",
            purpose="Determine whether one job, worker, queue, tenant, schedule, or environment is affected.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Compare with an approved successful run or equivalent schedule.",
                "Record schedule, worker, queue, tenant, environment, duration, and outcome differences.",
                "Preserve timestamps and original statuses without editing job metadata.",
            ],
            evidence_to_capture=["schedule", "worker", "queue", "tenant", "environment", "duration", "outcome"],
        ),
        GuidedCheck(
            check_id="review-read-only-scheduler-evidence",
            name="Review scheduler, worker, queue, and dependency evidence",
            purpose="Correlate the missed or failed run with objective availability, backlog, lease, lock, timeout, or dependency signals.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only dashboards, logs, queue views, and dependency status pages.",
                "Record the time window, component label, backlog depth, worker state, lease or lock signal, timeout, and correlation identifier.",
                "Do not purge queues, reset offsets, release locks, restart workers, or change concurrency.",
            ],
            evidence_to_capture=["time window", "component", "backlog", "worker state", "lease or lock", "timeout", "correlation ID"],
        ),
    ]

    return PlaybookResult(
        playbook_id="background-job-scheduler-failure",
        title="Background job or scheduler failure",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates a scheduled or background execution was missed, failed, stuck, delayed, or exhausted retries."]
            if applicable
            else ["The current evidence does not yet distinguish a scheduler or worker failure from file transfer, integration, data, or service failure."]
        ),
        confirmed_observation_ids=[
            item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The scheduler may not have dispatched the expected run, or a worker may not have accepted it.",
            "A worker, queue, lease, lock, timeout, retry, or dependency condition may have prevented completion.",
            "A schedule, deployment, credential, configuration, or dependency change may be temporally related.",
            "The job may have completed partially while downstream processing, acknowledgement, or status persistence failed.",
        ],
        escalation_criteria=[
            "A critical scheduled process is overdue, repeatedly failing, or accumulating backlog.",
            "A stable error code, exhausted-retry state, dead-letter item, stuck lease, or failed worker is captured.",
            "Multiple jobs, workers, queues, tenants, or environments show the same failure pattern.",
            "No approved alternative processing path exists for a blocked business process.",
        ],
        safety_warnings=[
            "A missed schedule, failed status, backlog, lock, or worker metric is evidence; it does not by itself prove the root cause.",
            "Do not manually trigger, retry, cancel, reschedule, skip, or duplicate production jobs without an approved runbook and authorization.",
            "Do not purge queues, reset offsets, release locks or leases, edit job state, restart workers, change concurrency, or disable safeguards during diagnosis.",
            "Redact payloads, credentials, personal data, tenant details, internal endpoints, and restricted business information before sharing.",
        ],
    )
