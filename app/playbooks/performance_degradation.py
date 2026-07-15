from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_performance_degradation(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    performance_signal = any(
        phrase in searchable
        for phrase in (
            "slow",
            "slowness",
            "performance degradation",
            "high latency",
            "response time",
            "takes minutes",
            "timed out after",
            "intermittent timeout",
            "saturation",
        )
    )
    hard_availability_signal = any(
        phrase in searchable
        for phrase in ("502", "503", "504", "service unavailable", "bad gateway", "gateway timeout")
    )
    authentication_or_authorization = any(
        phrase in searchable
        for phrase in ("cannot log in", "authentication failed", "401", "403", "access denied", "forbidden")
    )
    applicable = performance_signal and not hard_availability_signal and not authentication_or_authorization

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("timing_observation", "performance_measurement", "reproduction_result")):
        missing.append("Measured response time with operation, timestamp, client, and environment")
    if not any(kind in evidence_types for kind in ("baseline", "working_example", "comparison")):
        missing.append("Known-good baseline or comparison for the same operation")
    if not any(kind in evidence_types for kind in ("scope_comparison", "location_comparison", "user_comparison")):
        missing.append("Scope comparison across users, locations, clients, instances, or environments")
    if not any(kind in evidence_types for kind in ("resource_snapshot", "monitoring_snapshot", "dependency_status", "query_timing")):
        missing.append("Approved read-only resource, dependency, request, or query timing evidence")
    if not any(kind in evidence_types for kind in ("recent_change", "deployment", "configuration_change", "change_record")):
        missing.append("Recent deployment, configuration, data-volume, traffic, infrastructure, or dependency-change context")

    checks = [
        GuidedCheck(
            check_id="measure-one-approved-operation",
            name="Measure one approved operation consistently",
            purpose="Turn a subjective slowness report into a bounded, repeatable timing observation.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use one approved read-only operation and a small fixed number of attempts.",
                "Record start time, end time, duration, client, environment, result, and correlation identifier when available.",
                "Stop if attempts increase impact or the service is visibly degrading.",
            ],
            evidence_to_capture=["operation", "attempt count", "start time", "duration", "client", "environment", "result", "correlation ID"],
        ),
        GuidedCheck(
            check_id="compare-baseline-and-scope",
            name="Compare with a baseline and affected scope",
            purpose="Determine whether degradation is operation-specific, user-specific, location-specific, instance-specific, or broad.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Compare the same operation with a known-good period, approved user, client, location, or environment.",
                "Keep request volume minimal and equivalent across comparisons.",
                "Record material differences without clearing caches, changing clients, or bypassing controls as a fix.",
            ],
            evidence_to_capture=["baseline period", "comparison dimension", "duration", "result", "timestamp"],
        ),
        GuidedCheck(
            check_id="review-read-only-performance-evidence",
            name="Review approved read-only performance evidence",
            purpose="Correlate user-visible delay with request, dependency, database, queue, resource, or capacity signals.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only dashboards, traces, logs, query timing, or dependency views.",
                "Record the same time window and correlation identifier as the measured operation.",
                "Do not enable new production tracing, run expensive queries, change indexes, clear caches, restart, or scale as part of diagnosis.",
            ],
            evidence_to_capture=["time window", "request or query duration", "dependency duration", "resource signal", "queue depth", "correlation ID"],
        ),
    ]

    return PlaybookResult(
        playbook_id="performance-degradation",
        title="Performance degradation or excessive latency",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates the application or a specific operation remains available but responds materially slower than expected."]
            if applicable
            else ["The current evidence does not yet distinguish performance degradation from availability, authentication, authorization, client, or isolated application failure."]
        ),
        confirmed_observation_ids=[
            item.observation_id
            for item in observations
            if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "Application, database, dependency, network, storage, or external-service latency may have increased.",
            "Resource saturation, queue growth, contention, locking, connection-pool pressure, or workload change may be contributing.",
            "The issue may be isolated to one operation, data set, user context, location, client, instance, or environment.",
            "A deployment, configuration, data-volume, traffic, infrastructure, or dependency change may be temporally related.",
        ],
        escalation_criteria=[
            "Measured latency materially exceeds a known-good baseline using the same approved operation.",
            "Multiple approved users, clients, locations, or instances reproduce the degradation.",
            "Read-only evidence correlates the same time window with saturation, queueing, locking, slow queries, or dependency latency.",
            "A critical business process is delayed beyond its operational threshold and no approved alternative exists.",
        ],
        safety_warnings=[
            "A slow response, high metric, recent change, or correlation does not by itself prove root cause.",
            "Do not load-test, stress-test, run unbounded retries, execute expensive production queries, enable intrusive tracing, or collect payloads without authorization.",
            "Do not clear caches, rebuild indexes, change query plans, restart, scale, tune, or modify configuration without an approved runbook and authorization.",
            "Redact internal URLs, hostnames, query text, identifiers, payload data, and restricted performance telemetry before external sharing when required.",
        ],
    )
