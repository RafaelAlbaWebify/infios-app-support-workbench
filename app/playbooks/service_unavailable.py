from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_service_unavailable(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [
            support_case.title,
            support_case.application,
            support_case.impact,
            support_case.affected_scope,
        ]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    availability_signal = any(
        phrase in searchable
        for phrase in (
            "502",
            "bad gateway",
            "503",
            "service unavailable",
            "504",
            "gateway timeout",
            "upstream unavailable",
            "upstream timeout",
            "no healthy upstream",
        )
    )
    authentication_signal = any(
        phrase in searchable
        for phrase in (
            "cannot log in",
            "login failed",
            "sign-in failed",
            "authentication failed",
            "invalid credentials",
        )
    )
    authorization_signal = any(
        phrase in searchable
        for phrase in (
            "401",
            "403",
            "access denied",
            "forbidden",
            "not authorized",
        )
    )
    direct_application_failure = any(
        phrase in searchable
        for phrase in (
            "500 internal server error",
            "application exception",
            "stack trace",
            "unhandled exception",
        )
    )
    applicable = availability_signal and not authentication_signal and not authorization_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("http_observation", "api_response", "error_message")):
        missing.append("Sanitized 502/503/504 response, gateway message, or exact availability error")
    if not any(kind in evidence_types for kind in ("reproduction", "reproduction_result")):
        missing.append("Reproduction result with URL or operation, timestamp, client, and environment")
    if not any(kind in evidence_types for kind in ("scope_comparison", "location_comparison", "working_example", "comparison")):
        missing.append("Comparison across users, locations, clients, instances, or environments")
    if not any(kind in evidence_types for kind in ("health_check", "dependency_status", "service_status", "monitoring_snapshot")):
        missing.append("Approved read-only health or dependency status evidence")
    if not any(kind in evidence_types for kind in ("recent_change", "deployment", "configuration_change", "change_record")):
        missing.append("Recent deployment, routing, capacity, certificate, network, or dependency-change context")

    checks = [
        GuidedCheck(
            check_id="capture-availability-boundary",
            name="Capture the exact availability boundary",
            purpose="Confirm which client operation, endpoint, gateway, or dependency boundary returns the availability signal.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Repeat only the approved read-only request or navigation needed to reproduce the symptom.",
                "Record the sanitized status, response message, URL or operation, timestamp, duration, environment, and correlation identifier when available.",
                "Do not infer the failed component solely from a gateway-generated status code.",
            ],
            evidence_to_capture=["HTTP status", "sanitized response", "URL or operation", "timestamp", "duration", "environment", "correlation ID"],
        ),
        GuidedCheck(
            check_id="compare-scope-and-path",
            name="Compare scope and request path",
            purpose="Determine whether the symptom is isolated to one user, location, client, route, instance, or environment.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved clients, test accounts, and read-only operations only.",
                "Compare the same operation from another approved location or environment when available.",
                "Record differences without bypassing proxies, gateways, policies, or access controls.",
            ],
            evidence_to_capture=["user or account type", "location", "client", "route", "environment", "instance", "result", "timestamp"],
        ),
        GuidedCheck(
            check_id="review-read-only-health-evidence",
            name="Review approved health and dependency evidence",
            purpose="Correlate the request failure with objective service, gateway, instance, dependency, or capacity signals without changing the system.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only dashboards, health endpoints, logs, or status views.",
                "Record the time window, affected component label, health state, saturation or timeout signal, and correlation identifier.",
                "Do not restart, fail over, scale, drain, redeploy, or alter routing as part of diagnosis.",
            ],
            evidence_to_capture=["time window", "component label", "health state", "capacity or timeout signal", "correlation ID"],
        ),
    ]

    reasons: list[str]
    if applicable:
        reasons = ["Evidence indicates a gateway, proxy, load balancer, service, or upstream availability response such as HTTP 502, 503, or 504."]
    elif direct_application_failure:
        reasons = ["The current evidence points more directly to an application-side failure than to a gateway or upstream availability response."]
    else:
        reasons = ["The current evidence does not yet distinguish service unavailability from authentication, authorization, application, client, or network failure."]

    return PlaybookResult(
        playbook_id="service-unavailable",
        title="Service unavailable or gateway failure",
        applicable=applicable,
        applicability_reasons=reasons,
        confirmed_observation_ids=[
            item.observation_id
            for item in observations
            if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "A gateway, proxy, or load balancer may be unable to reach or receive a timely response from an upstream target.",
            "One or more service instances or dependencies may be unhealthy, unavailable, saturated, starting, draining, or outside the expected pool.",
            "Connection, DNS, TLS, routing, firewall, or proxy behavior between layers may be interrupting the request path.",
            "A deployment, configuration, certificate, capacity, or dependency change may be temporally related.",
        ],
        escalation_criteria=[
            "Multiple approved users, locations, clients, or environments reproduce the same 502/503/504 response.",
            "A stable gateway message, upstream timeout, no-healthy-target signal, correlation ID, or affected component is captured.",
            "Approved health evidence shows an unhealthy dependency, exhausted capacity, repeated timeout, or instance-level failure in the same time window.",
            "A critical business process is blocked and no approved alternative path exists.",
        ],
        safety_warnings=[
            "HTTP 502, 503, or 504 identifies an observed response boundary; it does not by itself prove which gateway, service, instance, dependency, network path, or change is the root cause.",
            "Do not restart services, recycle pools, fail over, scale, drain instances, redeploy, modify routing, disable health checks, or bypass gateways without an approved runbook and authorization.",
            "Do not repeatedly load-test or retry a degraded production service; use bounded, approved reproduction attempts.",
            "Redact internal hostnames, URLs, IP addresses, correlation data, tenant details, and restricted infrastructure information before external sharing when required.",
        ],
    )
