from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_dependency_outage(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    dependency_signal = any(
        phrase in searchable
        for phrase in (
            "dependency outage", "upstream outage", "downstream outage", "third-party outage", "vendor outage",
            "dependency unavailable", "upstream unavailable", "downstream unavailable", "service dependency",
            "provider incident", "partner unavailable", "external service down", "dependency timeout",
        )
    )
    direct_app_signal = any(phrase in searchable for phrase in ("local validation error", "client-side error", "feature bug"))
    applicable = dependency_signal and not direct_app_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("dependency_error", "error_message", "timeout", "availability_result")):
        missing.append("Exact sanitized dependency error, timeout, status, and timestamp")
    if not any(kind in evidence_types for kind in ("dependency_status", "status_page", "health_check", "monitoring_snapshot")):
        missing.append("Approved read-only dependency health, provider status, or monitoring evidence")
    if not any(kind in evidence_types for kind in ("scope_comparison", "dependency_comparison", "working_example")):
        missing.append("Comparison across dependency, endpoint, region, environment, tenant, or known-good path")
    if not any(kind in evidence_types for kind in ("request_trace", "correlation_trace", "dependency_timing", "network_path")):
        missing.append("Request/correlation trace showing the boundary between the application and dependency")
    if not any(kind in evidence_types for kind in ("recent_change", "provider_notice", "deployment", "change_record")):
        missing.append("Recent provider notice, endpoint, routing, deployment, credential, quota, or configuration context")

    checks = [
        GuidedCheck(
            check_id="capture-dependency-boundary",
            name="Capture the exact dependency boundary",
            purpose="Identify the calling component, dependency, operation, timestamp, status, duration, and correlation identifier.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved application logs, traces, dashboards, and provider status evidence.",
                "Record the dependency label, operation, timestamp, status/error, duration, and correlation identifier.",
                "Do not infer that a gateway code proves which dependency failed.",
            ],
            evidence_to_capture=["calling component", "dependency", "operation", "timestamp", "status", "duration", "correlation ID"],
        ),
        GuidedCheck(
            check_id="compare-dependency-scope",
            name="Compare dependency scope and known-good paths",
            purpose="Determine whether one endpoint, region, tenant, environment, provider, or request type is affected.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Compare approved status, timing, and outcome evidence with a known-good dependency or path.",
                "Record endpoint label, region, environment, tenant, request type, and outcome differences.",
                "Do not switch endpoints, regions, providers, credentials, or routing during diagnosis.",
            ],
            evidence_to_capture=["endpoint", "region", "environment", "tenant", "request type", "outcome"],
        ),
        GuidedCheck(
            check_id="review-provider-and-local-evidence",
            name="Review provider and local dependency evidence",
            purpose="Correlate provider status with local DNS, network, TLS, quota, timeout, and circuit-breaker signals.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only provider notices, dashboards, traces, and network-path evidence.",
                "Record time-window alignment and any difference between provider-wide and local observations.",
                "Do not disable circuit breakers, increase retries, bypass quotas, restart services, or force failover.",
            ],
            evidence_to_capture=["provider status", "local status", "DNS/path", "TLS", "quota", "timeout", "circuit breaker"],
        ),
    ]

    return PlaybookResult(
        playbook_id="dependency-outage",
        title="Dependency outage",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates an upstream, downstream, provider, partner, or service dependency may be unavailable or timing out."]
            if applicable
            else ["The current evidence does not yet distinguish a dependency outage from an internal application, gateway, network, access, or data failure."]
        ),
        confirmed_observation_ids=[
            item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The dependency or one of its regional endpoints may be unavailable, degraded, rate-limited, or timing out.",
            "A local DNS, network, proxy, TLS, credential, quota, or routing condition may prevent access while the provider remains healthy.",
            "A circuit breaker, retry policy, connection pool, or timeout boundary may be exposing or amplifying dependency failure.",
            "A provider incident, endpoint change, deployment, quota change, or configuration change may be temporally related.",
        ],
        escalation_criteria=[
            "A critical dependency is confirmed unavailable or degraded by provider and local evidence.",
            "Multiple applications, regions, tenants, or environments show the same dependency boundary failure.",
            "A stable timeout, quota, circuit-breaker, TLS, DNS, or network-path signal is captured.",
            "Business processing is blocked and no approved degraded mode or alternative dependency path exists.",
        ],
        safety_warnings=[
            "A provider notice, gateway error, timeout, or recent change is evidence; it does not by itself prove the root cause or failing component.",
            "Do not force failover, change providers/endpoints/routing, disable circuit breakers, increase retries, bypass quotas, restart services, or alter credentials without an approved runbook and authorization.",
            "Avoid repeated production probes or retries that could increase load, cost, duplicate transactions, or provider throttling.",
            "Redact credentials, tokens, payloads, tenant data, internal endpoints, account identifiers, and restricted provider information.",
        ],
    )
