from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_intermittent_incident(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    intermittent_signal = any(
        phrase in searchable
        for phrase in (
            "intermittent", "sporadic", "sometimes fails", "works sometimes", "random failure",
            "occasionally", "flapping", "transient", "cannot reproduce consistently", "recurs", "comes and goes",
        )
    )
    applicable = intermittent_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("occurrence_log", "incident_timeline", "error_message", "reproduction_result")):
        missing.append("Occurrence timeline with successes and failures, absolute timestamps, operation, scope, and sanitized error evidence")
    if not any(kind in evidence_types for kind in ("scope_comparison", "client_comparison", "instance_comparison", "working_example")):
        missing.append("Comparison across user, client, instance, node, region, tenant, environment, request type, or data shape")
    if not any(kind in evidence_types for kind in ("correlation_trace", "request_trace", "log_sample", "monitoring_snapshot")):
        missing.append("Correlation IDs and approved logs/metrics for matched successful and failed occurrences")
    if not any(kind in evidence_types for kind in ("frequency_sample", "rate_sample", "bounded_measurement", "pattern_analysis")):
        missing.append("Bounded sample showing frequency, duration, time window, and denominator without generating uncontrolled load")
    if not any(kind in evidence_types for kind in ("recent_change", "dependency_status", "capacity_snapshot", "schedule_context")):
        missing.append("Recent change, dependency, capacity, schedule, routing, session, or lifecycle context for the affected windows")

    checks = [
        GuidedCheck(
            check_id="capture-occurrence-pattern",
            name="Capture a bounded occurrence pattern",
            purpose="Record a finite sample of successes and failures without creating uncontrolled retries or additional impact.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use existing approved logs, monitoring, user reports, or a strictly bounded low-risk reproduction.",
                "Record absolute timestamp, operation, outcome, duration, scope, error, and correlation identifier for each occurrence.",
                "Stop sampling if it increases load, duplicates transactions, changes data, or worsens impact.",
            ],
            evidence_to_capture=["timestamp", "operation", "outcome", "duration", "scope", "error", "correlation ID"],
        ),
        GuidedCheck(
            check_id="compare-success-and-failure",
            name="Compare matched successful and failed occurrences",
            purpose="Identify objective differences in client, instance, node, path, data, session, timing, dependency, and version context.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Choose comparable success/failure pairs from the same operation and bounded time window.",
                "Record only observed differences and preserve unknown values explicitly.",
                "Do not treat a difference as causal without supporting mechanism evidence.",
            ],
            evidence_to_capture=["client", "instance/node", "path", "data shape", "session", "time", "dependency", "version"],
        ),
        GuidedCheck(
            check_id="review-pattern-correlations",
            name="Review approved pattern correlations",
            purpose="Correlate occurrences with capacity, lifecycle, routing, schedules, deployments, dependencies, and network/TLS evidence.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only dashboards, logs, traces, change records, and dependency evidence.",
                "Record supporting and contradicting evidence for each candidate pattern.",
                "Do not restart, recycle, drain, fail over, clear caches, reset sessions, or change routing/configuration during diagnosis.",
            ],
            evidence_to_capture=["capacity", "lifecycle", "routing", "schedule", "deployment", "dependency", "network/TLS"],
        ),
    ]

    return PlaybookResult(
        playbook_id="intermittent-incident",
        title="Intermittent incident",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates the symptom is sporadic, transient, recurring, flapping, or not consistently reproducible."]
            if applicable
            else ["The current evidence does not establish an intermittent pattern; investigate the primary symptom and build a bounded occurrence timeline."]
        ),
        confirmed_observation_ids=[
            item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The symptom may follow one instance, node, client, region, tenant, data shape, session state, or request path.",
            "Capacity, timing, pool, queue, lifecycle, cache, race, retry, routing, network, TLS, or dependency conditions may vary between occurrences.",
            "A scheduled task, deployment, autoscaling event, certificate lifecycle, token/session lifecycle, or provider event may be temporally related.",
            "The apparent randomness may reflect incomplete sampling, mismatched comparisons, or missing correlation across system boundaries.",
        ],
        escalation_criteria=[
            "The intermittent failure affects a critical workflow or creates data integrity, duplicate-processing, or safety risk.",
            "A stable pattern by node, path, tenant, region, data shape, time window, or dependency is captured.",
            "The frequency or impact is increasing, or the incident cannot be safely reproduced at L1.",
            "Diagnosis would require intrusive tracing, production load, restart, failover, routing, configuration, or data changes.",
        ],
        safety_warnings=[
            "Intermittent does not mean random. Record unknowns and observed patterns without inventing a cause.",
            "Do not use uncontrolled retries, load tests, repeated transactions, or broad production probing to force reproduction.",
            "Do not restart, recycle, drain, fail over, clear caches, reset sessions, terminate connections, or change routing/configuration without an approved runbook and authorization.",
            "A correlation or repeated pattern is evidence, not automatic causation; confirmed explanations still require supporting observations and explicit operator confirmation.",
        ],
    )
