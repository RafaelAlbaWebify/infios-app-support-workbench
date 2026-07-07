# INFIOS - Application Support Workbench

[![INFIOS CI](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml)

**Incident Flow & Information Operations Support**

INFIOS is a local-first Application Support Engineering workbench. It turns messy application incidents into structured evidence, safe next steps, escalation notes, RCA drafts, and Markdown reports.

The first MVP focuses on one realistic support scenario:

> A user receives HTTP 500 after login.

## Purpose

This repository is designed as portfolio proof for Application Support Engineer, Software Support Engineer, Technical Support Engineer II, and Production Support Engineer roles.

It demonstrates:

- HTTP/API incident interpretation.
- Evidence-first troubleshooting.
- User impact analysis.
- Missing evidence identification.
- Safe support next steps.
- Vendor/developer escalation quality.
- RCA discipline without pretending to know the root cause without evidence.

## Safety Boundaries

INFIOS is local-first and sample-data only.

It does not:

- connect to production systems;
- store credentials or secrets;
- process real customer data;
- modify databases;
- auto-remediate issues;
- claim confirmed root cause without evidence.

## MVP API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service health |
| GET | `/api/samples` | List available sample incidents |
| POST | `/api/analyze` | Analyze an incident JSON |
| POST | `/api/report/markdown` | Generate a Markdown report |

<!-- INFIOS_SCENARIOS_START -->
## Scenarios

| Milestone | Sample | Support focus | Status |
|---|---|---|---|
| M1 | `incident-500-login.json` | HTTP 500 after login; evidence-first application failure triage, safe next steps, escalation and RCA draft | Published |
| M2 | `incident-403-after-login.json` | HTTP 403 after login; authentication vs authorization separation, role/group/claim evidence and access escalation | Published |
| M2.1 | Docs and report-quality cleanup | Cleaner report wording, interview notes, milestone status and support-ready explanation | Published |

<!-- INFIOS_SCENARIOS_END -->

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pytest -q
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```


## Demo Reports

Generated example reports are included here:

```text
reports/sample-500-login-report.md
reports/sample-403-access-report.md
```

These reports show support-ready outputs for HTTP/API incidents: incident summary, user impact, evidence table, likely causes not confirmed, unknowns, missing evidence, safe next steps, escalation note and RCA draft.


## Support Notes

Additional portfolio support notes are included here:

```text
docs/interview-notes.md
docs/milestone-status.md
```

These notes explain what INFIOS is, how to discuss it in interviews, what each scenario demonstrates, and where the project is going next.

## Interview Explanation

> INFIOS is my Application Support Engineering workbench. It is currently an API-first/backend application that turns messy application incidents into structured evidence, safe next steps, escalation notes and RCA drafts. The first scenario handles HTTP 500 after login, where I keep root cause uncertain until logs and dependency evidence confirm it. The second scenario handles HTTP 403 after login, where I separate authentication from authorization and check role, group, claim and route-permission evidence before suggesting any access change.
