# INFIOS - Application Support Workbench

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

## Interview Explanation

> INFIOS is my Application Support Engineering workbench. I built it to practice handling messy incidents like HTTP 500 after login. The goal is not to guess the root cause, but to structure the evidence: who is affected, what changed, what logs show, what is still unknown, what safe checks should be done next, and what a good escalation to developers or a vendor should include. It reflects the way I work in production support: evidence first, clear user impact, and no risky changes without confirmation.
