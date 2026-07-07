from __future__ import annotations

from app.models import AnalysisResult, Finding, IncidentInput


def _case_text(incident: IncidentInput) -> str:
    return " ".join(
        [
            incident.title,
            incident.symptom,
            incident.user_impact,
            incident.operator_notes or "",
            " ".join(incident.recent_changes),
            " ".join(item.detail for item in incident.evidence),
        ]
    ).lower()


def _has_text(incident: IncidentInput, *needles: str) -> bool:
    haystack = _case_text(incident)
    return any(needle.lower() in haystack for needle in needles)


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

    if incident.http_status == 500 or _has_text(incident, "http 500", "500 internal server error", "internal server error"):
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

    if _has_text(incident, "login", "sign in", "authentication"):
        findings.append(
            Finding(
                category="Login flow",
                severity="medium",
                statement="The symptom occurs around login, so authentication, session creation, user profile loading, and post-login authorization should be separated.",
                evidence_refs=["title", "symptom"],
            )
        )
        safe_next_steps.extend(
            [
                "Confirm whether credentials are accepted before the error appears.",
                "Check whether the failure happens before login, at callback, or after landing page load.",
                "Compare one affected user with a known working user with the same role.",
            ]
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

    if "database" not in " ".join(item.detail.lower() for item in incident.evidence):
        missing_evidence.append("Database or dependency health evidence, if login loads profile/session data.")

    unknowns.extend(
        [
            "Exact failure point in the login flow.",
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

    likely_causes = list(dict.fromkeys(likely_causes)) or [
        "The available evidence is not enough to propose a likely cause safely."
    ]

    unknowns = list(dict.fromkeys(unknowns))
    missing_evidence = list(dict.fromkeys(missing_evidence))
    safe_next_steps = list(dict.fromkeys(safe_next_steps))

    escalation_note = (
        f"Please investigate incident {incident.incident_id}: {incident.title}. "
        f"Impact: {incident.user_impact}. "
        f"Observed symptom: {incident.symptom}. "
        f"HTTP status: {incident.http_status or 'unknown'}. "
        f"Endpoint: {incident.endpoint or 'unknown'}. "
        f"Correlation ID: {incident.correlation_id or 'not provided'}. "
        "Requested support: review application logs and dependency calls around the incident timestamp and confirm the failing component."
    )

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
