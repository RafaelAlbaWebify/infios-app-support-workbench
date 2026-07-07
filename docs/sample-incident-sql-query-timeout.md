# INFIOS M6 - SQL Evidence Scenario

## Scenario

A reporting page loads, but generating a daily order report returns HTTP 500 after a SQL query timeout.

This scenario is designed to practice Application Support triage around SQL-dependent applications without pretending to be a DBA and without connecting to any real database.

## Support focus

The goal is to separate:

- application symptom: user receives HTTP 500;
- operation: which report, endpoint, date range, or parameter set fails;
- SQL evidence: error text, timeout duration, query/stored procedure name, and sanitized parameters;
- scope: one user, one report, one site, one date range, or all reporting users;
- ownership: application development, DBA/database platform, reporting owner, integration owner, or support configuration;
- safe action boundary: support can collect and structure evidence, but should not modify data, schema, indexes, sessions, services, or connection strings without approval.

## Evidence to collect

- exact timestamp;
- endpoint or report route;
- HTTP status;
- correlation/request ID;
- application log entry;
- SQL error text and error number if available;
- stored procedure/query/view/report name;
- sanitized parameters such as date range, site, or report filter;
- observed duration or timeout threshold;
- comparison with a known working parameter set;
- recent deployment, schema, job, data-load, or reporting configuration changes;
- owner-provided read-only database evidence such as blocking, waits, job status, connection pool, or report duration.

## Safe boundaries

Do not run write queries, update data, change indexes, change schema, kill sessions, restart SQL services, change connection strings, or modify production reports without owner approval.

## Interview explanation

> I added a SQL evidence scenario because many Application Support roles involve SQL-dependent applications. I do not claim to be a DBA. I focus on collecting the right evidence: the endpoint, timestamp, correlation ID, SQL error text, stored procedure or query name, sanitized parameters, affected scope, and recent changes. Then I escalate safely to the right owner without running write queries or changing the database.
