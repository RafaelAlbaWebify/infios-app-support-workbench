from __future__ import annotations

from app.models import AnalysisResult, Finding, IncidentInput


def _case_text(incident: IncidentInput) -> str:
    return " ".join(
        [
            incident.title,
            incident.symptom,
            incident.user_impact,
            incident.operator_notes or "",
            incident.endpoint or "",
            str(incident.http_status or ""),
            " ".join(incident.recent_changes),
            " ".join(item.detail for item in incident.evidence),
        ]
    ).lower()


def _has_text(incident: IncidentInput, *needles: str) -> bool:
    haystack = _case_text(incident)
    return any(needle.lower() in haystack for needle in needles)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _sentence_fragment(value: str | None, fallback: str = "unknown") -> str:
    if value is None:
        return fallback
    cleaned = value.strip().rstrip(".")
    return cleaned or fallback


def _is_http_500_case(incident: IncidentInput) -> bool:
    return incident.http_status == 500 or _has_text(
        incident,
        "http 500",
        "500 internal server error",
        "internal server error",
    )


def _is_access_denied_case(incident: IncidentInput) -> bool:
    return incident.http_status in {401, 403} or _has_text(
        incident,
        "http 401",
        "401 unauthorized",
        "unauthorized",
        "http 403",
        "403 forbidden",
        "forbidden",
        "access denied",
        "not authorized",
        "not authorised",
        "permission denied",
        "authorization",
        "authorisation",
    )


def _is_dependency_unavailable_case(incident: IncidentInput) -> bool:
    return incident.http_status in {502, 503, 504} or _has_text(
        incident,
        "http 502",
        "bad gateway",
        "http 503",
        "service unavailable",
        "http 504",
        "gateway timeout",
        "dependency unavailable",
        "downstream unavailable",
        "downstream api",
        "timeout",
        "connection refused",
        "circuit breaker",
        "health check failing",
        "queue unavailable",
    )


def _add_login_flow_guidance(
    incident: IncidentInput,
    findings: list[Finding],
    safe_next_steps: list[str],
    *,
    access_denied: bool,
) -> None:
    if not _has_text(incident, "login", "sign in", "authentication", "after login", "post-login"):
        return

    findings.append(
        Finding(
            category="Login flow",
            severity="medium",
            statement="The symptom occurs around login, so authentication, session creation, user profile loading, and post-login authorization should be separated.",
            evidence_refs=["title", "symptom"],
        )
    )

    if access_denied:
        safe_next_steps.append(
            "Map the flow stage precisely: credential validation, callback/session creation, landing page, then protected resource access."
        )
        return

    safe_next_steps.extend(
        [
            "Confirm whether credentials are accepted before the error appears.",
            "Check whether the failure happens before login, at callback, after callback, or after landing page load.",
            "Compare one affected user with a known working user with the same role.",
        ]
    )


def analyze_incident(incident: IncidentInput) -> AnalysisResult:
    findings: list[Finding] = []
    likely_causes: list[str] = []
    unknowns: list[str] = []
    missing_evidence: list[str] = []
    safe_next_steps: list[str] = []

    summary = (
        f"{incident.affected_service} is reporting '{incident.symptom}'. "
        "This is being treated as an Application Support case with evidence-first analysis."
    )

    is_http_500 = _is_http_500_case(incident)
    is_access_denied = _is_access_denied_case(incident)
    is_dependency_unavailable = _is_dependency_unavailable_case(incident)

    if is_http_500:
        findings.append(
            Finding(
                category="HTTP",
                severity="high",
                statement="HTTP 500 indicates the server failed while processing the request. It does not prove root cause by itself.",
                evidence_refs=["http_status", "symptom"],
            )
        )
        likely_causes.extend(
            [
                "Unhandled application exception during or after login.",
                "Backend dependency failure after authentication, such as database, identity, session, or downstream API.",
                "Configuration or deployment issue affecting the login callback or post-login route.",
            ]
        )
        safe_next_steps.extend(
            [
                "Reproduce the login flow with a sample or test user if available.",
                "Collect exact timestamp, endpoint, HTTP status, browser observation, and correlation ID.",
                "Check application logs around the timestamp for exception class, stack trace, and failed dependency.",
                "Compare affected user scope: one user, one role, one site, or all users.",
            ]
        )

    if is_access_denied:
        severity = "high" if incident.http_status == 403 else "medium"
        findings.append(
            Finding(
                category="Access control",
                severity=severity,
                statement="The symptom indicates an authentication or authorization boundary. Separate credential validation, session/token creation, role mapping, and application permission checks.",
                evidence_refs=["http_status", "symptom", "endpoint"],
            )
        )

        if incident.http_status == 401:
            findings.append(
                Finding(
                    category="Authentication",
                    severity="medium",
                    statement="HTTP 401 usually means the request is not authenticated or the session/token is missing, expired, invalid, or not accepted by the application.",
                    evidence_refs=["http_status"],
                )
            )
            likely_causes.extend(
                [
                    "Expired, missing, or invalid session/token after login.",
                    "Identity provider callback or application session configuration issue.",
                    "Cookie, redirect, or token validation problem between the browser and application.",
                ]
            )

        if incident.http_status == 403:
            findings.append(
                Finding(
                    category="Authorization",
                    severity="high",
                    statement="HTTP 403 usually means the user is authenticated but the application denies access to the requested resource.",
                    evidence_refs=["http_status", "endpoint"],
                )
            )
            likely_causes.extend(
                [
                    "User is authenticated but missing the required application role, group membership, claim, or permission.",
                    "Application role mapping or authorization rule is stale, misconfigured, or recently changed.",
                    "The requested route or resource is restricted to a different role, tenant, site, or business unit.",
                ]
            )

        likely_causes.extend(
            [
                "Mismatch between identity provider groups/claims and application authorization rules.",
                "Recent access-control or deployment change affecting the post-login route.",
            ]
        )

        safe_next_steps.extend(
            [
                "Confirm whether credentials are accepted before the access error appears.",
                "Compare the affected user with a known working user in the same role and business context.",
                "Collect application authorization logs around the timestamp and endpoint.",
                "Check identity provider sign-in/authentication evidence separately from application authorization evidence.",
                "Verify expected group membership, app role assignment, claims, tenant/site scope, and route permission.",
                "Do not add permissions or change groups until the required access model is confirmed by the application owner.",
            ]
        )

        missing_evidence.extend(
            [
                "Identity provider sign-in evidence showing whether authentication succeeded.",
                "Application authorization log entry for the failed endpoint and user.",
                "Expected role/group/app-permission evidence for the affected resource.",
                "Comparison with a known working user in the same business role.",
            ]
        )

    if is_dependency_unavailable:
        findings.append(
            Finding(
                category="Dependency",
                severity="high",
                statement="The symptom indicates the application may be reachable while a required downstream dependency is unavailable, degraded, timing out, or rejecting requests.",
                evidence_refs=["http_status", "symptom", "endpoint"],
            )
        )

        if incident.http_status == 503:
            findings.append(
                Finding(
                    category="Service availability",
                    severity="high",
                    statement="HTTP 503 usually means the service or one of its dependencies is temporarily unavailable. It should be correlated with health checks, dependency logs, and recent changes.",
                    evidence_refs=["http_status"],
                )
            )

        if incident.http_status == 504:
            findings.append(
                Finding(
                    category="Timeout",
                    severity="high",
                    statement="HTTP 504 usually points to a gateway or upstream timeout and should be investigated as a dependency latency or reachability issue.",
                    evidence_refs=["http_status"],
                )
            )

        likely_causes.extend(
            [
                "Downstream API, database, queue, cache, or integration service is unavailable or degraded.",
                "Dependency timeout, connection pool exhaustion, circuit breaker opening, or rate limit affecting the request path.",
                "Recent deployment, configuration, certificate, DNS, firewall, or routing change affecting a dependency.",
                "Application is healthy enough to respond but cannot complete the operation because a required dependency is failing.",
            ]
        )

        missing_evidence.extend(
            [
                "Dependency health-check result for the same timestamp.",
                "Application log entry showing the downstream dependency name and failure mode.",
                "Dependency owner/status confirmation or monitoring evidence.",
                "Network, DNS, TLS/certificate, or firewall evidence if the dependency is external or cross-service.",
            ]
        )

        safe_next_steps.extend(
            [
                "Identify the exact failing dependency, operation, endpoint, and timestamp from application logs.",
                "Compare application health with dependency health; do not assume the frontend service itself is the root cause.",
                "Check dependency health checks, monitoring, recent deployments, and known maintenance windows.",
                "Review timeout, retry, circuit-breaker, queue, and connection-pool evidence before restarting anything.",
                "Test or compare a different operation that does not use the suspected dependency, if safe sample data is available.",
                "Escalate with impact, endpoint, correlation ID, dependency name, failure mode, and recent-change context.",
            ]
        )

        unknowns.extend(
            [
                "Which dependency is failing and whether it is fully down, degraded, slow, rate-limited, or misconfigured.",
                "Whether the issue affects all users, one operation, one region/site, or one integration path.",
                "Whether retries, circuit breakers, queues, or cached responses are masking the real blast radius.",
            ]
        )

    _add_login_flow_guidance(
        incident,
        findings,
        safe_next_steps,
        access_denied=is_access_denied,
    )

    if incident.correlation_id:
        findings.append(
            Finding(
                category="Traceability",
                severity="info",
                statement="A correlation ID is available and should be used to find exact server-side log entries.",
                evidence_refs=["correlation_id"],
            )
        )
    else:
        missing_evidence.append("Correlation ID or request ID from the failed request.")

    if not incident.evidence:
        missing_evidence.append("Application log entry from the same timestamp as the user error.")
    else:
        findings.append(
            Finding(
                category="Evidence",
                severity="info",
                statement=f"{len(incident.evidence)} evidence item(s) were provided for initial analysis.",
                evidence_refs=[item.source for item in incident.evidence],
            )
        )

    if not incident.recent_changes:
        unknowns.append("Whether there were recent deployments, configuration changes, certificate changes, identity provider changes, or database changes.")
    else:
        findings.append(
            Finding(
                category="Recent changes",
                severity="medium",
                statement="Recent changes exist and should be compared with the incident start time.",
                evidence_refs=["recent_changes"],
            )
        )

    evidence_text = " ".join(item.detail.lower() for item in incident.evidence)
    if "database" not in evidence_text and is_http_500:
        missing_evidence.append("Database or dependency health evidence, if login loads profile/session data.")

    unknowns.extend(
        [
            "Exact failure point in the login, access, or dependency flow.",
            "Whether the issue affects all users or only a subset.",
            "Whether the error is reproducible from another browser, device, or network.",
        ]
    )

    safe_next_steps.extend(
        [
            "Do not restart services or modify data without evidence and approval.",
            "Prepare escalation with impact, timestamps, endpoint, correlation ID, reproduction steps, and collected logs.",
            "Keep user-facing updates factual: impact, workaround if known, and next investigation step.",
        ]
    )

    likely_causes = _dedupe(likely_causes) or [
        "The available evidence is not enough to propose a likely cause safely."
    ]
    unknowns = _dedupe(unknowns)
    missing_evidence = _dedupe(missing_evidence)
    safe_next_steps = _dedupe(safe_next_steps)

    escalation_note = (
        f"Please investigate incident {incident.incident_id}: {_sentence_fragment(incident.title)}. "
        f"Impact: {_sentence_fragment(incident.user_impact)}. "
        f"Observed symptom: {_sentence_fragment(incident.symptom)}. "
        f"HTTP status: {incident.http_status or 'unknown'}. "
        f"Endpoint: {incident.endpoint or 'unknown'}. "
        f"Correlation ID: {incident.correlation_id or 'not provided'}. "
    )

    if is_dependency_unavailable and not is_access_denied:
        escalation_note += (
            "Requested support: review application logs, dependency health, monitoring, recent changes, and connectivity evidence around the incident timestamp, then confirm the failing dependency or service boundary."
        )
    else:
        escalation_note += (
            "Requested support: review application logs, identity/session evidence, and dependency calls around the incident timestamp, then confirm the failing component or access rule."
        )

    if is_dependency_unavailable and not is_access_denied and not is_http_500:
        rca_draft = (
            "RCA draft: The confirmed root cause is not yet known. Current evidence shows a service-availability or dependency failure "
            "visible to the user during a specific operation. Next RCA update should confirm the failing dependency, failure mode, blast radius, "
            "corrective action, and preventive monitoring or resilience improvement."
        )
    elif is_access_denied and not is_http_500:
        rca_draft = (
            "RCA draft: The confirmed root cause is not yet known. Current evidence shows an access-control failure "
            "visible to the user during or after login. Next RCA update should confirm whether authentication succeeded, "
            "which authorization rule denied access, the affected user scope, the corrective action, and the preventive control."
        )
    else:
        rca_draft = (
            "RCA draft: The confirmed root cause is not yet known. Current evidence shows an application-side failure "
            "visible to the user during the login flow. Next RCA update should confirm the failing component, trigger, "
            "blast radius, resolution, and preventive action after logs and dependency evidence are reviewed."
        )

    return AnalysisResult(
        incident_id=incident.incident_id,
        summary=summary,
        user_impact=incident.user_impact,
        likely_causes=likely_causes,
        unknowns=unknowns,
        missing_evidence=missing_evidence,
        safe_next_steps=safe_next_steps,
        escalation_note=escalation_note,
        rca_draft=rca_draft,
        findings=findings,
    )
