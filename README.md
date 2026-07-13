# INFIOS - Application Support Workbench

[![INFIOS CI](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml)

**Incident Flow & Information Operations Support**

INFIOS is a local-first Application Support Engineering workbench. It helps support teams turn fragmented application incidents into structured cases containing evidence, traceable observations, guided checks, diagnostic actions, possible explanations, escalation packages, recovery validation, and cautious RCA material.

## Current development status

The persistent investigation workflow is being developed on the draft pull-request branch `architecture/investigation-workbench`. The `main` branch remains the published compatibility baseline until the new slice is reviewed and merged.

## Purpose

This repository is designed both as portfolio proof for Application Support Engineer, Software Support Engineer, Technical Support Engineer II, and Production Support Engineer roles, and as the foundation of a practical incident-investigation tool for L1 and L2 support teams.

INFIOS is not an autonomous root-cause engine. It preserves the distinction between reported information, technically confirmed observations, possible explanations, completed diagnostic actions, recovery validation, and unresolved unknowns.

## Persistent investigation workflow

```text
Create case
→ add evidence
→ create evidence-backed observations
→ evaluate a guided playbook
→ create/start/complete diagnostic actions
→ track possible explanations
→ generate an L2 escalation package
→ validate recovery with supporting evidence
→ review the complete case summary and timeline
```

### Case endpoints

- `POST /api/cases`
- `GET /api/cases`
- `GET /api/cases/{case_id}`
- `POST /api/cases/{case_id}/status`
- `GET /api/cases/{case_id}/summary`

### Evidence endpoints

- `POST /api/cases/{case_id}/evidence`
- `GET /api/cases/{case_id}/evidence`
- `GET /api/cases/{case_id}/evidence/{evidence_id}`

### Observation endpoints

- `POST /api/cases/{case_id}/observations`
- `GET /api/cases/{case_id}/observations`
- `GET /api/cases/{case_id}/observations/{observation_id}`

### Guided playbook endpoint

- `GET /api/cases/{case_id}/playbooks/post-login-feature-failure`

### Diagnostic-action endpoints

- `POST /api/cases/{case_id}/actions`
- `GET /api/cases/{case_id}/actions`
- `GET /api/cases/{case_id}/actions/{action_id}`
- `POST /api/cases/{case_id}/actions/{action_id}/start`
- `POST /api/cases/{case_id}/actions/{action_id}/complete`

### Possible-explanation endpoints

- `POST /api/cases/{case_id}/explanations`
- `GET /api/cases/{case_id}/explanations`
- `GET /api/cases/{case_id}/explanations/{explanation_id}`
- `POST /api/cases/{case_id}/explanations/{explanation_id}/status`

### Escalation endpoints

- `POST /api/cases/{case_id}/escalations`
- `GET /api/cases/{case_id}/escalations`
- `GET /api/cases/{case_id}/escalations/{package_id}`

### Recovery-validation endpoints

- `POST /api/cases/{case_id}/recovery-validations`
- `GET /api/cases/{case_id}/recovery-validations`
- `GET /api/cases/{case_id}/recovery-validations/{validation_id}`

### Timeline endpoint

- `GET /api/cases/{case_id}/timeline`

The timeline includes case creation, evidence, observations, diagnostic-action starts and completions, generated escalation packages, and recovery-validation outcomes.

## Safety principles

- Sample or sanitized data only.
- No production credentials or unrestricted production logs.
- No automated remediation.
- No SQL writes or production configuration changes.
- Restart/write actions cannot be represented as L1-safe.
- Every factual observation must reference evidence from the same case.
- Possible explanations must reference same-case observations and actions.
- Pattern matching can propose explanations but cannot confirm root cause.
- A confirmed explanation requires explicit operator confirmation and supporting observations.
- A passed recovery validation requires supporting evidence from the same case.

## Legacy compatibility

The original scenario analyzer, CLI, sample incidents, Markdown reports, JSON output, and local run history remain available while the persistent workbench is developed alongside them.

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

Generate the log-pattern report and save local run history:

```powershell
python -m app.cli analyze samples/incident-log-pattern-correlation.json --out reports/generated/cli-log-pattern-demo.md --save-history
```

Use the installed command after setup:

```powershell
infios analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md
```

Print JSON analysis output:

```powershell
python -m app.cli analyze samples/incident-403-after-login.json --format json
```

## Demo Reports

Generated example reports remain available under `reports/`, including:

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

These reports demonstrate incident summaries, user impact, evidence tables, unconfirmed possible causes, missing evidence, safe next steps, escalation notes, RCA drafts, and local run-history records.

## Support Notes

Additional portfolio and workflow documentation is available under `docs/`, including the architecture, development workflow, CLI usage, run history, sample incidents, demo commands, milestone status, and interview notes.

## Development verification

GitHub Actions installs the package and runs the complete automated test suite for every pull-request update. CI uploads `pytest.log` as a short-lived artifact, making failures directly inspectable. Repository-native CI is the default proof loop; local PowerShell and manual testing are reserved for Windows-specific packaging and later usability or visual validation.
