# INFIOS Interview Notes

## What INFIOS is

INFIOS is a local-first Application Support Engineering workbench.

At the current stage it is an API-first/backend application, not a polished frontend product. It uses FastAPI, Pydantic models, analyzer rules, sample incidents, Markdown report generation, tests, and GitHub Actions CI.

The purpose is to demonstrate support engineering capability: turning messy application incidents into structured evidence, safe next steps, escalation notes and RCA drafts.

## How to explain it naturally

> INFIOS is my Application Support Engineering workbench. I built it to practice the way I would handle messy application incidents: collect evidence, separate symptoms from possible causes, identify missing information, avoid unsafe actions, and prepare a clear escalation or RCA draft.

## M1 - HTTP 500 after login

This scenario shows that I understand HTTP 500 as a server-side symptom, not a confirmed root cause.

I separate:

- user impact;
- login flow stage;
- endpoint and status;
- correlation ID;
- application logs;
- possible backend dependencies;
- unknowns and missing evidence.

Natural explanation:

> In the HTTP 500 scenario, I do not say the database or the application is definitely broken. I treat it as an application-side failure visible to the user and prepare the evidence a developer or vendor would need: timestamp, endpoint, HTTP status, correlation ID, reproduction notes and logs.

## M2 - HTTP 403 after login

This scenario shows that I understand the difference between authentication and authorization.

I separate:

- successful credential validation;
- session or token creation;
- application role mapping;
- group or claim evidence;
- route/resource permission;
- comparison with a known working user.

Natural explanation:

> In the HTTP 403 scenario, the user may be authenticated, but the application denies access to a resource. I avoid saying “login is broken” too quickly. I check roles, groups, claims, route permissions and application authorization logs before proposing any access change.

## Support boundaries

INFIOS is sample-data only. It does not connect to production systems, store credentials, process real customer data, modify databases, auto-remediate issues, or claim confirmed root cause without evidence.

## What this proves for Application Support Engineer roles

- HTTP/API incident interpretation.
- Evidence-first troubleshooting.
- Safe escalation quality.
- RCA discipline.
- Access troubleshooting thinking.
- Clear support communication.
- Practical scripting/backend capability without pretending to be a senior developer or DBA.
