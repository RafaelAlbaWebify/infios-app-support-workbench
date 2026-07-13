# INFIOS - Application Support Workbench

[![INFIOS CI](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml)

**Incident Flow & Information Operations Support**

INFIOS is a local-first Application Support Engineering workbench. It turns messy application incidents into structured evidence, safe next steps, escalation notes, RCA drafts, Markdown reports, JSON analysis output, and local run-history records.

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
- CLI-based local tooling.
- Local run-history traceability.
- SQL/database evidence handling without DBA overclaiming.
- Application log-pattern evidence handling.

## Safety Boundaries

INFIOS is local-first and sample-data only.

It does not:

- connect to production systems;
- store credentials or secrets;
- process real customer data;
- collect production log dumps;
- modify databases;
- run SQL queries against real systems;
- auto-remediate issues;
- claim confirmed root cause without evidence.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service health |
| GET | `/api/samples` | List available sample incidents |
| GET | `/api/history` | List local run-history records |
| POST | `/api/analyze` | Analyze an incident JSON |
| POST | `/api/report/markdown` | Generate a Markdown report |
| POST | `/api/report/markdown/save` | Generate a Markdown report and save local run history |

<!-- INFIOS_SCENARIOS_START -->
## Scenarios

| Milestone | Sample | Support focus | Status |
|---|---|---|---|
| M1 | `incident-500-login.json` | HTTP 500 after login; evidence-first application failure triage, safe next steps, escalation and RCA draft | Published |
| M2 | `incident-403-after-login.json` | HTTP 403 after login; authentication vs authorization separation, role/group/claim evidence and access escalation | Published |
| M2.1 | Docs and report-quality cleanup | Cleaner report wording, interview notes, milestone status and support-ready explanation | Published |
| M3 | `incident-503-dependency.json` | HTTP 503 dependency unavailable; application vs downstream dependency boundary, health evidence and dependency escalation | Published |
| M4 | CLI runner | Analyze local incident JSON and generate Markdown or JSON output from the terminal | Published |
| M5 | Local run history | Save timestamped local JSON records for CLI/API analysis runs | Published |
| M6 | `incident-sql-query-timeout.json` | SQL evidence scenario; query timeout evidence, safe read-only boundaries and database-owner escalation | Published |
| M6.1 | README and demo polish | Clean demo commands, clearer README structure, and README formatting regression tests | Published |
| M7 | `incident-log-pattern-correlation.json` | Log-pattern evidence scenario; repeated error signatures, correlation IDs, time windows and redacted escalation | Published |

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

## Demo Commands

Generate the HTTP 503 dependency report:

```powershell
python -m app.cli analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md
```

Generate the SQL timeout report:

```powershell
python -m app.cli analyze samples/incident-sql-query-timeout.json --out reports/generated/cli-sql-timeout-demo.md
```

Generate the log-pattern report:

```powershell
python -m app.cli analyze samples/incident-log-pattern-correlation.json --out reports/generated/cli-log-pattern-demo.md
```

Generate a log-pattern report and save a local run-history record:

```powershell
python -m app.cli analyze samples/incident-log-pattern-correlation.json --out reports/generated/cli-log-pattern-demo.md --save-history
```

Use the installed console command after `pip install -e ".[dev]"`:

```powershell
infios analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md
```

Print JSON analysis output:

```powershell
python -m app.cli analyze samples/incident-403-after-login.json --format json
```

## Demo Reports

Generated example reports are included here:

```text
reports/sample-500-login-report.md
reports/sample-403-access-report.md
reports/sample-503-dependency-report.md
reports/sample-sql-query-timeout-report.md
reports/sample-log-pattern-report.md
reports/generated/cli-503-demo.md
reports/generated/cli-503-history-demo.json
reports/generated/cli-sql-timeout-history-demo.json
reports/generated/cli-log-pattern-history-demo.json
```

These reports show support-ready outputs for HTTP/API incidents: incident summary, user impact, evidence table, likely causes not confirmed, unknowns, missing evidence, safe next steps, escalation note, RCA draft, and local run-history records.

## Support Notes

Additional portfolio support notes are included here:

```text
docs/interview-notes.md
docs/milestone-status.md
docs/sample-incident-503-dependency.md
docs/cli-usage.md
docs/run-history.md
docs/sample-incident-sql-query-timeout.md
docs/sample-incident-log-pattern.md
docs/demo-commands.md
```

These notes explain what INFIOS is, how to discuss it in interviews, what each scenario demonstrates, and where the project is going next.

## Interview Explanation

> INFIOS is my Application Support Engineering workbench. It is currently an API-first/backend application with a CLI runner and local run history. It turns local sample incidents into structured evidence, safe next steps, escalation notes, RCA drafts and timestamped run records. The scenarios cover HTTP 500 application failure, HTTP 403 authorization failure, HTTP 503 dependency unavailable, SQL query timeout evidence, and repeated log-pattern evidence. The log scenario is deliberately safe: it structures representative redacted log evidence without collecting production log dumps, secrets, tokens, session IDs, or personal data.
