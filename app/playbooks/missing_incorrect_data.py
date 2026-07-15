from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_missing_incorrect_data(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    data_signal = any(
        phrase in searchable
        for phrase in (
            "missing data", "incorrect data", "wrong data", "stale data", "outdated data",
            "record missing", "duplicate record", "data mismatch", "not synchronized",
            "sync delay", "wrong value", "blank field", "incomplete record", "data not updated",
        )
    )
    transfer_signal = any(phrase in searchable for phrase in ("file import failed", "file export failed", "sftp", "ftp transfer"))
    integration_signal = any(phrase in searchable for phrase in ("invalid payload", "schema validation", "webhook failed", "api failure"))
    applicable = data_signal and not transfer_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("user_report", "data_sample", "screenshot", "record_comparison")):
        missing.append("Sanitized affected record, field, expected value, observed value, source, and timestamp")
    if not any(kind in evidence_types for kind in ("reproduction", "reproduction_result", "query_result")):
        missing.append("Bounded read-only reproduction showing where the value is missing, stale, duplicated, or incorrect")
    if not any(kind in evidence_types for kind in ("source_comparison", "record_comparison", "working_example", "comparison")):
        missing.append("Comparison between source, intermediate, and displayed/persisted values using sanitized identifiers")
    if not any(kind in evidence_types for kind in ("timeline", "sync_status", "processing_status", "audit_log")):
        missing.append("Approved read-only processing, synchronization, audit, or update-timestamp evidence")
    if not any(kind in evidence_types for kind in ("recent_change", "deployment", "mapping_change", "schema_change", "change_record")):
        missing.append("Recent mapping, schema, deployment, cache, synchronization, or source-data change context")

    checks = [
        GuidedCheck(
            check_id="define-data-discrepancy",
            name="Define the exact data discrepancy",
            purpose="Separate missing, stale, duplicated, transformed, displayed, or persisted-data symptoms.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Record the business object, field, expected value, observed value, source, environment, and relevant timestamps.",
                "Use sanitized identifiers and the smallest data sample needed to demonstrate the discrepancy.",
                "Do not edit, re-save, delete, or recreate the affected production record during diagnosis.",
            ],
            evidence_to_capture=["object type", "field", "expected value", "observed value", "source", "timestamps", "environment"],
        ),
        GuidedCheck(
            check_id="trace-read-only-data-path",
            name="Trace the data path using approved read-only evidence",
            purpose="Locate the first boundary where source, transformed, synchronized, persisted, or displayed values diverge.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Compare approved source, intermediate, database/API, and UI views without changing records.",
                "Record update timestamps, versions, mapping labels, processing states, and sanitized identifiers.",
                "Treat a recent change or stale timestamp as context, not proof of root cause.",
            ],
            evidence_to_capture=["boundary", "source value", "target value", "update timestamp", "version or mapping", "processing state"],
        ),
        GuidedCheck(
            check_id="compare-scope-and-known-good-record",
            name="Compare scope and a known-good record",
            purpose="Determine whether the discrepancy is record-specific, field-specific, user-specific, batch-specific, or systemic.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use a sanitized known-good record with the same type and expected processing path.",
                "Compare only approved read-only fields, timestamps, source, batch, tenant, location, and version context.",
                "Do not force synchronization, clear caches, rerun jobs, repair data, or backfill records as part of diagnosis.",
            ],
            evidence_to_capture=["record type", "field differences", "batch or source", "tenant or location", "timestamps", "result"],
        ),
    ]

    if applicable:
        reasons = ["Evidence indicates missing, stale, duplicated, incomplete, mismatched, or incorrect application data."]
    elif transfer_signal:
        reasons = ["The current evidence points to file transfer/import/export failure; use that playbook when available."]
    elif integration_signal:
        reasons = ["The current evidence may originate at an API contract or payload boundary; use the API/integration playbook first."]
    else:
        reasons = ["The current evidence does not yet distinguish a data discrepancy from display, integration, processing, synchronization, or user-entry behavior."]

    return PlaybookResult(
        playbook_id="missing-incorrect-data",
        title="Missing or incorrect data",
        applicable=applicable,
        applicability_reasons=reasons,
        confirmed_observation_ids=[item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The source record may be missing, incomplete, duplicated, stale, or different from the expected business state.",
            "A mapping, transformation, synchronization, filtering, caching, persistence, or display boundary may alter or delay the value.",
            "The affected record may differ by batch, tenant, location, version, effective date, status, or processing path.",
            "A deployment, mapping, schema, source-data, cache, or synchronization change may be temporally related.",
        ],
        escalation_criteria=[
            "Multiple sanitized records, fields, users, batches, tenants, or environments show the same discrepancy.",
            "The first divergent boundary, mapping/version difference, stale timestamp, processing state, or audit signal is captured.",
            "Source and target values remain inconsistent after the expected processing window without an approved explanation.",
            "A critical business process or regulatory record is affected and no approved workaround exists.",
        ],
        safety_warnings=[
            "A mismatch, stale timestamp, duplicate, missing record, or recent change is evidence; it does not by itself prove the root cause.",
            "Do not expose personal, financial, regulated, or restricted business data; use sanitized identifiers and minimal samples.",
            "Do not edit, delete, recreate, re-save, backfill, force synchronization, clear caches, rerun jobs, or repair production data without an approved runbook, authorization, and rollback plan.",
            "Preserve the original observed values and timestamps so diagnostic activity does not overwrite evidence.",
        ],
    )
