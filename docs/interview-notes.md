# INFIOS Interview Notes

## What INFIOS is

INFIOS is a local-first Application Support Engineering workbench.

At the current stage it is an API-first/backend application with a CLI runner and local run history, not a polished frontend product. It uses FastAPI, Pydantic models, analyzer rules, sample incidents, Markdown report generation, tests, GitHub Actions CI, terminal-based report generation, and local JSON run records.

The purpose is to demonstrate support engineering capability: turning messy application incidents into structured evidence, safe next steps, escalation notes and RCA drafts.

## How to explain it naturally

> INFIOS is my Application Support Engineering workbench. I built it to practice the way I would handle messy application incidents: collect evidence, separate symptoms from possible causes, identify missing information, avoid unsafe actions, and prepare a clear escalation or RCA draft. It can run as an API backend, I can use it from the terminal, and it can save a local run-history record for traceability.

## M1 - HTTP 500 after login

This scenario shows that I understand HTTP 500 as a server-side symptom, not a confirmed root cause.

Natural explanation:

> In the HTTP 500 scenario, I do not say the database or the application is definitely broken. I treat it as an application-side failure visible to the user and prepare the evidence a developer or vendor would need: timestamp, endpoint, HTTP status, correlation ID, reproduction notes and logs.

## M2 - HTTP 403 after login

This scenario shows that I understand the difference between authentication and authorization.

Natural explanation:

> In the HTTP 403 scenario, the user may be authenticated, but the application denies access to a resource. I avoid saying "login is broken" too quickly. I check roles, groups, claims, route permissions and application authorization logs before proposing any access change.

## M3 - HTTP 503 dependency unavailable

This scenario shows that I understand dependency/service-health triage.

Natural explanation:

> In the HTTP 503 scenario, I do not assume the whole application is down. I check whether the app is reachable and whether a specific dependency is failing. Then I collect timestamp, endpoint, correlation ID, dependency health, logs and recent changes so the escalation identifies the right owner and failure boundary.

## M4 - CLI runner

This milestone shows that INFIOS is becoming a usable local tool, not only an API backend.

Natural explanation:

> I added a CLI runner so I can analyze a local sample incident from the terminal and generate a Markdown report. This makes the tool easier to demo and also keeps the design local-first and safe, because it reads sample JSON and writes local reports only.

## M5 - Local run history

This milestone adds traceability to local analysis runs.

Natural explanation:

> I added local run history so each analysis can leave a timestamped JSON record with the incident ID, service, HTTP status, endpoint, finding categories, severity counts and report path. This mirrors support discipline: every analysis should leave enough traceability for review, handover or follow-up.

## M6 - SQL evidence scenario

This milestone shows SQL-dependent application support thinking without pretending to be a DBA.

Natural explanation:

> I added a SQL evidence scenario because many Application Support roles involve data-dependent applications. I do not claim to be a DBA. I collect the evidence support should provide: timestamp, endpoint, correlation ID, SQL error text, stored procedure or query name, sanitized parameters, affected scope and recent changes. I also make the safety boundary explicit: no write queries, no data updates, no index or schema changes, no killing sessions and no restarts without owner approval.

## Support boundaries

INFIOS is sample-data only. It does not connect to production systems, store credentials, process real customer data, modify databases, auto-remediate issues, or claim confirmed root cause without evidence.

## What this proves for Application Support Engineer roles

- HTTP/API incident interpretation.
- Evidence-first troubleshooting.
- Safe escalation quality.
- RCA discipline.
- Access troubleshooting thinking.
- Dependency and service-health triage.
- SQL/database evidence handling.
- Local evidence traceability.
- Practical local tooling.
- Clear support communication.
- Practical scripting/backend capability without pretending to be a senior developer or DBA.
