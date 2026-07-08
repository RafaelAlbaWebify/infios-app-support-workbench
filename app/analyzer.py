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


def _is_sql_evidence_case(incident: IncidentInput) -> bool:
    return _has_text(
        incident,
        "sql",
        "database",
        "db",
        "query timeout",
        "timeout expired",
        "stored procedure",
        "procedure",
        "deadlock",
        "blocking",
        "lock wait",
        "connection pool",
        "slow query",
        "execution plan",
        "index",
        "table",
        "missing row",
        "reference data",
        "stale data",
    )


def _is_log_pattern_case(incident: IncidentInput) -> bool:
    haystack = _case_text(incident)

    log_context_terms = (
        "application log",
        "error log",
        "log pattern",
        "log sample",
        "stack trace",
        "traceback",
        "exception=",
        "exception ",
        "error signature",
        "same error signature",
    )
    pattern_terms = (
        "repeated",
        "multiple occurrences",
        "same error",
        "error signature",
        "exception",
        "stack trace",
        "first seen",
        "last seen",
        "occurrence count",
        "error burst",
        "error rate",
        "correlationid=",
    )

    has_log_context = any(term in haystack for term in log_context_terms)
    has_pattern_signal = any(term in haystack for term in pattern_terms)
    return has_log_context and has_pattern_signal


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
    is_sql_evidence = _is_sql_evidence_case(incident)
    is_log_pattern = _is_log_pattern_case(incident)

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

    if is_sql_evidence:
        findings.append(
            Finding(
                category="SQL evidence",
                severity="high",
                statement="The available evidence mentions SQL or database behavior. Treat this as a data-dependency support case and separate application symptoms from database evidence before claiming root cause.",
                evidence_refs=["evidence", "operator_notes"],
            )
        )
        findings.append(
            Finding(
                category="Database dependency",
                severity="medium",
                statement="Database-related symptoms should be validated with safe, read-only evidence such as error text, query/procedure name, duration, affected parameters, blocking/wait evidence, and owner confirmation.",
                evidence_refs=["recent_changes", "evidence"],
            )
        )

        likely_causes.extend(
            [
                "SQL query, stored procedure, view, or report operation is timing out or returning an application error.",
                "Database blocking, wait contention, stale statistics, missing index, execution plan change, or data-volume change may be affecting the request.",
                "Connection pool exhaustion, database connectivity instability, or read-only dependency degradation may be visible through the application.",
                "Recent deployment, schema change, data load, reference-data change, or reporting configuration change may have affected the SQL path.",
            ]
        )

        missing_evidence.extend(
            [
                "Exact SQL error text, error number, timeout duration, stored procedure/query name, and sanitized parameters.",
                "Application log entry linking the correlation ID to the database operation.",
                "Read-only database health evidence from the responsible owner, such as blocking/wait state, connection pool, job status, or report duration.",
                "Comparison of affected versus working parameters, date ranges, user/site scope, or reference-data inputs.",
            ]
        )

        safe_next_steps.extend(
            [
                "Collect the application log entry with correlation ID, SQL error text, procedure/query name, duration, and sanitized parameters.",
                "Confirm whether the issue affects one report/query path, one date range, one site, one user group, or all users.",
                "Compare with a known working parameter set or shorter date range using sample-safe or approved test data only.",
                "Ask the database/application owner for read-only evidence around blocking, waits, connection pool, failed jobs, recent schema/data changes, or plan/regression indicators.",
                "Do not run write queries, change indexes, update data, kill sessions, restart SQL services, or change connection strings without owner approval.",
                "Escalate with impact, timestamp, endpoint, correlation ID, SQL operation name, sanitized parameters, observed duration, and missing evidence.",
            ]
        )

        unknowns.extend(
            [
                "Whether the SQL evidence points to query logic, data volume, blocking/waits, connection pool pressure, stale/reference data, or an application-side handling problem.",
                "Whether the failure is reproducible with a safe sample, smaller date range, or known working parameters.",
                "Whether the responsible owner is application development, DBA/database platform, reporting, integration, or support configuration.",
            ]
        )

    if is_log_pattern:
        findings.append(
            Finding(
                category="Log pattern",
                severity="high",
                statement="The evidence contains application log signals. Correlate timestamp, endpoint, correlation/request ID, exception text, and repeated occurrences before claiming root cause.",
                evidence_refs=["evidence", "correlation_id"],
            )
        )
        findings.append(
            Finding(
                category="Error clustering",
                severity="medium",
                statement="Repeated or similar log entries should be grouped by error signature, endpoint, correlation/request ID, deployment window, and affected scope.",
                evidence_refs=["evidence", "recent_changes"],
            )
        )

        likely_causes.extend(
            [
                "A repeated application exception may be affecting one endpoint, operation, feature flag, deployment version, or input pattern.",
                "A recent deployment or configuration change may have introduced a recurring error signature.",
                "A downstream dependency, data path, access rule, or application code path may be failing consistently for the same request pattern.",
                "A noisy log symptom may be secondary; the primary failure must be confirmed by correlation ID, timestamp sequence, and owner validation.",
            ]
        )

        missing_evidence.extend(
            [
                "Exact log lines around the incident timestamp, with sensitive values redacted.",
                "Error signature or exception class grouped across repeated occurrences.",
                "Count of repeated errors in the affected time window compared with a normal baseline.",
                "Request/correlation IDs that link user reports, application logs, and any downstream dependency logs.",
                "Deployment version, host/container/instance identifier, and feature flag/config state if available.",
            ]
        )

        safe_next_steps.extend(
            [
                "Group log entries by timestamp, endpoint, correlation ID, exception class, message fingerprint, host/instance, and recent deployment window.",
                "Confirm whether the same error signature appears before and after the first user report.",
                "Compare error frequency during the incident window with a normal baseline or previous known-good period.",
                "Separate primary failure evidence from secondary noise, retries, warnings, and follow-on errors.",
                "Redact tokens, session IDs, personal data, and secrets before sharing logs in escalation notes.",
                "Escalate with the shortest representative log excerpt, occurrence count, affected endpoint, correlation IDs, first/last seen timestamps, and recent-change context.",
            ]
        )

        unknowns.extend(
            [
                "Whether the repeated log pattern is the primary failure or secondary noise.",
                "Whether the pattern affects one endpoint, one user group, one host/instance, one deployment version, or all traffic.",
                "Whether the error began after a deployment, configuration change, data change, dependency incident, or traffic pattern change.",
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
            "Exact failure point in the login, access, dependency, data, or log sequence.",
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

    if is_sql_evidence:
        escalation_note += (
            "Requested support: review application logs and safe read-only SQL/database evidence around the incident timestamp, including query/procedure name, sanitized parameters, timeout/error text, blocking/wait or connection-pool evidence, and recent data/schema/job changes. Do not perform write actions without owner approval."
        )
    elif is_log_pattern:
        escalation_note += (
            "Requested support: review the representative log pattern around the incident window, including first/last seen timestamps, occurrence count, endpoint, correlation IDs, exception signature, affected host/instance, and recent-change context. Please confirm whether the pattern is primary failure evidence or secondary noise."
        )
    elif is_dependency_unavailable and not is_access_denied:
        escalation_note += (
            "Requested support: review application logs, dependency health, monitoring, recent changes, and connectivity evidence around the incident timestamp, then confirm the failing dependency or service boundary."
        )
    else:
        escalation_note += (
            "Requested support: review application logs, identity/session evidence, and dependency calls around the incident timestamp, then confirm the failing component or access rule."
        )

    if is_sql_evidence:
        rca_draft = (
            "RCA draft: The confirmed root cause is not yet known. Current evidence shows a SQL/database-dependent operation "
            "failing through the application. Next RCA update should confirm the exact query/procedure or database dependency, "
            "failure mode, affected parameters, blast radius, corrective action, and preventive monitoring or validation control."
        )
    elif is_log_pattern:
        rca_draft = (
            "RCA draft: The confirmed root cause is not yet known. Current evidence shows a repeated application log pattern "
            "correlated with the user-visible incident. Next RCA update should confirm the representative error signature, first and last seen timestamps, "
            "affected scope, triggering change or condition, corrective action, and monitoring or alerting improvement."
        )
    elif is_dependency_unavailable and not is_access_denied and not is_http_500:
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

