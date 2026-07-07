# INFIOS Incident Report - INFIOS-SAMPLE-SQL-TIMEOUT

## Incident Summary

Order Reporting Portal is reporting 'The report page loads, but generating the daily order report returns HTTP 500 after a SQL query timeout.'. This is being treated as an Application Support case with evidence-first analysis.

## User Impact

Business users cannot generate the daily order report for the selected date range. Operational impact depends on whether the issue affects one report, one site, or all reporting users.

## Incident Metadata

| Field | Value |
|---|---|
| Title | Daily order report returns HTTP 500 after SQL timeout |
| Service | Order Reporting Portal |
| Environment | sample |
| HTTP Status | 500 |
| Endpoint | /reports/orders/daily |
| Correlation ID | sample-corr-20260708-090500-sql001 |

## Evidence Table

| Source | Timestamp | Confidence | Detail |
|---|---:|---|---|
| user report | 2026-07-08T09:05:00+02:00 | medium | User reports the daily order report fails for a large date range but the application menu still loads. |
| browser observation | 2026-07-08T09:07:00+02:00 | high | HTTP 500 observed on /reports/orders/daily after clicking Generate Report. |
| application log sample | 2026-07-08T09:07:04+02:00 | medium | Sample log references correlation ID sample-corr-20260708-090500-sql001 and SQL timeout expired while executing stored procedure sample_sp_daily_order_report. |
| support note | 2026-07-08T09:10:00+02:00 | medium | Smaller sample date range works; larger date range times out. No database writes or production queries were executed. |

## Findings

| Category | Severity | Statement | Evidence References |
|---|---|---|---|
| HTTP | high | HTTP 500 indicates the server failed while processing the request. It does not prove root cause by itself. | http_status, symptom |
| Dependency | high | The symptom indicates the application may be reachable while a required downstream dependency is unavailable, degraded, timing out, or rejecting requests. | http_status, symptom, endpoint |
| SQL evidence | high | The available evidence mentions SQL or database behavior. Treat this as a data-dependency support case and separate application symptoms from database evidence before claiming root cause. | evidence, operator_notes |
| Database dependency | medium | Database-related symptoms should be validated with safe, read-only evidence such as error text, query/procedure name, duration, affected parameters, blocking/wait evidence, and owner confirmation. | recent_changes, evidence |
| Traceability | info | A correlation ID is available and should be used to find exact server-side log entries. | correlation_id |
| Evidence | info | 4 evidence item(s) were provided for initial analysis. | user report, browser observation, application log sample, support note |
| Recent changes | medium | Recent changes exist and should be compared with the incident start time. | recent_changes |

## Likely Causes - Not Confirmed

- Unhandled application exception during or after login.
- Backend dependency failure after authentication, such as database, identity, session, or downstream API.
- Configuration or deployment issue affecting the login callback or post-login route.
- Downstream API, database, queue, cache, or integration service is unavailable or degraded.
- Dependency timeout, connection pool exhaustion, circuit breaker opening, or rate limit affecting the request path.
- Recent deployment, configuration, certificate, DNS, firewall, or routing change affecting a dependency.
- Application is healthy enough to respond but cannot complete the operation because a required dependency is failing.
- SQL query, stored procedure, view, or report operation is timing out or returning an application error.
- Database blocking, wait contention, stale statistics, missing index, execution plan change, or data-volume change may be affecting the request.
- Connection pool exhaustion, database connectivity instability, or read-only dependency degradation may be visible through the application.
- Recent deployment, schema change, data load, reference-data change, or reporting configuration change may have affected the SQL path.

## Unknowns

- Which dependency is failing and whether it is fully down, degraded, slow, rate-limited, or misconfigured.
- Whether the issue affects all users, one operation, one region/site, or one integration path.
- Whether retries, circuit breakers, queues, or cached responses are masking the real blast radius.
- Whether the SQL evidence points to query logic, data volume, blocking/waits, connection pool pressure, stale/reference data, or an application-side handling problem.
- Whether the failure is reproducible with a safe sample, smaller date range, or known working parameters.
- Whether the responsible owner is application development, DBA/database platform, reporting, integration, or support configuration.
- Exact failure point in the login, access, dependency, or data path.
- Whether the issue affects all users or only a subset.
- Whether the error is reproducible from another browser, device, or network.

## Missing Evidence

- Dependency health-check result for the same timestamp.
- Application log entry showing the downstream dependency name and failure mode.
- Dependency owner/status confirmation or monitoring evidence.
- Network, DNS, TLS/certificate, or firewall evidence if the dependency is external or cross-service.
- Exact SQL error text, error number, timeout duration, stored procedure/query name, and sanitized parameters.
- Application log entry linking the correlation ID to the database operation.
- Read-only database health evidence from the responsible owner, such as blocking/wait state, connection pool, job status, or report duration.
- Comparison of affected versus working parameters, date ranges, user/site scope, or reference-data inputs.

## Safe Next Steps

- Reproduce the login flow with a sample or test user if available.
- Collect exact timestamp, endpoint, HTTP status, browser observation, and correlation ID.
- Check application logs around the timestamp for exception class, stack trace, and failed dependency.
- Compare affected user scope: one user, one role, one site, or all users.
- Identify the exact failing dependency, operation, endpoint, and timestamp from application logs.
- Compare application health with dependency health; do not assume the frontend service itself is the root cause.
- Check dependency health checks, monitoring, recent deployments, and known maintenance windows.
- Review timeout, retry, circuit-breaker, queue, and connection-pool evidence before restarting anything.
- Test or compare a different operation that does not use the suspected dependency, if safe sample data is available.
- Escalate with impact, endpoint, correlation ID, dependency name, failure mode, and recent-change context.
- Collect the application log entry with correlation ID, SQL error text, procedure/query name, duration, and sanitized parameters.
- Confirm whether the issue affects one report/query path, one date range, one site, one user group, or all users.
- Compare with a known working parameter set or shorter date range using sample-safe or approved test data only.
- Ask the database/application owner for read-only evidence around blocking, waits, connection pool, failed jobs, recent schema/data changes, or plan/regression indicators.
- Do not run write queries, change indexes, update data, kill sessions, restart SQL services, or change connection strings without owner approval.
- Escalate with impact, timestamp, endpoint, correlation ID, SQL operation name, sanitized parameters, observed duration, and missing evidence.
- Do not restart services or modify data without evidence and approval.
- Prepare escalation with impact, timestamps, endpoint, correlation ID, reproduction steps, and collected logs.
- Keep user-facing updates factual: impact, workaround if known, and next investigation step.

## Escalation Note

Please investigate incident INFIOS-SAMPLE-SQL-TIMEOUT: Daily order report returns HTTP 500 after SQL timeout. Impact: Business users cannot generate the daily order report for the selected date range. Operational impact depends on whether the issue affects one report, one site, or all reporting users. Observed symptom: The report page loads, but generating the daily order report returns HTTP 500 after a SQL query timeout. HTTP status: 500. Endpoint: /reports/orders/daily. Correlation ID: sample-corr-20260708-090500-sql001. Requested support: review application logs and safe read-only SQL/database evidence around the incident timestamp, including query/procedure name, sanitized parameters, timeout/error text, blocking/wait or connection-pool evidence, and recent data/schema/job changes. Do not perform write actions without owner approval.

## RCA Draft

RCA draft: The confirmed root cause is not yet known. Current evidence shows a SQL/database-dependent operation failing through the application. Next RCA update should confirm the exact query/procedure or database dependency, failure mode, affected parameters, blast radius, corrective action, and preventive monitoring or validation control.

## Support Boundary

This report is evidence-first. It does not confirm root cause without logs, dependency evidence, or owner validation.
