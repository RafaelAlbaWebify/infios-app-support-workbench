from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_sql_database_connectivity(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    database_signal = any(
        phrase in searchable
        for phrase in (
            "database connection", "database unavailable", "sql connection", "sql timeout",
            "query timeout", "connection timeout", "login timeout", "connection pool exhausted",
            "too many connections", "deadlock", "database locked", "could not connect to database",
            "connection refused", "connection reset", "ora-", "sqlstate", "database is locked",
        )
    )
    access_signal = any(
        phrase in searchable
        for phrase in ("invalid credentials", "login failed for user", "permission denied", "access denied", "not authorized")
    )
    generic_latency_only = any(phrase in searchable for phrase in ("slow", "high latency", "takes too long")) and not database_signal
    applicable = database_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("database_error", "error_message", "log_excerpt", "application_log")):
        missing.append("Sanitized database error, SQLSTATE/vendor code, application message, and timestamp")
    if not any(kind in evidence_types for kind in ("reproduction", "reproduction_result", "query_result")):
        missing.append("Bounded reproduction result with operation, environment, duration, and timestamp")
    if not any(kind in evidence_types for kind in ("scope_comparison", "working_example", "comparison")):
        missing.append("Comparison across users, application instances, databases, or environments")
    if not any(kind in evidence_types for kind in ("database_status", "connection_pool", "monitoring_snapshot", "dependency_status")):
        missing.append("Approved read-only database, connection-pool, or dependency status evidence")
    if not any(kind in evidence_types for kind in ("recent_change", "deployment", "schema_change", "configuration_change", "change_record")):
        missing.append("Recent deployment, schema, credential, network, capacity, or configuration-change context")

    checks = [
        GuidedCheck(
            check_id="capture-database-boundary",
            name="Capture the exact database failure boundary",
            purpose="Identify whether the application fails while opening a connection, authenticating, acquiring a pooled connection, or executing a bounded operation.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Record the last successful application step and first database-related failure.",
                "Capture only sanitized error text, vendor code or SQLSTATE, timestamp, duration, environment, and correlation identifier.",
                "Do not copy connection strings, passwords, tokens, full queries containing sensitive data, or unrestricted result sets.",
            ],
            evidence_to_capture=["operation", "error code", "sanitized message", "timestamp", "duration", "environment", "correlation ID"],
        ),
        GuidedCheck(
            check_id="compare-approved-paths",
            name="Compare approved application and database paths",
            purpose="Determine whether the symptom is isolated to one operation, instance, database, account type, or environment.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use an approved read-only application operation or lightweight health query already covered by a runbook.",
                "Compare a known-good environment or instance when available.",
                "Stop after bounded attempts and do not repeatedly execute expensive or blocking queries.",
            ],
            evidence_to_capture=["operation", "instance", "database label", "environment", "duration", "result", "timestamp"],
        ),
        GuidedCheck(
            check_id="review-database-health-read-only",
            name="Review approved database and connection-pool evidence",
            purpose="Correlate the failure with objective connection, session, wait, lock, timeout, capacity, or availability signals without changing the database.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only dashboards, status views, application pool metrics, or existing diagnostic queries.",
                "Record the time window, connection count, pool state, timeout or wait signal, database health state, and affected component label.",
                "Do not kill sessions, clear pools, modify queries, rebuild indexes, change isolation, fail over, restart, or alter database configuration.",
            ],
            evidence_to_capture=["time window", "pool or session state", "timeout or wait signal", "database health", "component label"],
        ),
    ]

    if applicable:
        reasons = ["Evidence indicates a database connection, pool, timeout, lock, deadlock, or SQL execution boundary requiring database-focused investigation."]
    elif access_signal:
        reasons = ["The current evidence may involve database authentication or authorization, but does not yet establish a broader connectivity or timeout incident."]
    elif generic_latency_only:
        reasons = ["The current evidence shows general slowness without a database-specific signal; use the performance-degradation playbook first."]
    else:
        reasons = ["The current evidence does not yet distinguish database connectivity from application, network, access, or general performance failure."]

    return PlaybookResult(
        playbook_id="sql-database-connectivity",
        title="SQL or database connectivity and timeout failure",
        applicable=applicable,
        applicability_reasons=reasons,
        confirmed_observation_ids=[item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The application may be unable to open, authenticate, or retain a database connection.",
            "A connection pool, session limit, lock, deadlock, long-running transaction, or timeout may be affecting the operation.",
            "DNS, network, TLS, listener, failover, or routing behavior between the application and database may be involved.",
            "A deployment, schema, query, credential, capacity, or configuration change may be temporally related.",
        ],
        escalation_criteria=[
            "Multiple approved operations, instances, users, or environments reproduce the same database error or timeout.",
            "A stable SQLSTATE, vendor code, pool-exhaustion, deadlock, lock-wait, listener, or connectivity signal is captured.",
            "Approved read-only evidence shows unhealthy database state, exhausted sessions, repeated waits, or timeouts in the same window.",
            "A critical business process is blocked and no approved alternative exists.",
        ],
        safety_warnings=[
            "A database error code, timeout, lock, or high connection count is evidence; it does not by itself prove the root cause.",
            "Never collect or expose database passwords, connection-string secrets, tokens, private keys, or unrestricted production data.",
            "Do not run unbounded or expensive queries, kill sessions, clear pools, alter data, rebuild indexes, update statistics, change plans or isolation, fail over, restart, or modify database configuration without an approved runbook and authorization.",
            "Use bounded read-only checks and stop if diagnostic activity increases load, blocking, or user impact.",
        ],
    )
