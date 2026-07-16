# INFIOS — Application Support Workbench

[![INFIOS CI](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml)

**Incident Flow & Information Operations Support**

INFIOS is a local-first Application Support investigation workbench. It helps turn fragmented application incidents into structured, evidence-backed cases that are easier to troubleshoot, escalate and validate after recovery.

## The support problem

Application incidents often arrive as a mixture of user reports, logs, screenshots, HTTP errors, database clues, previous actions and assumptions.

INFIOS keeps those elements separate so the operator can distinguish:

- what the user reported;
- what the available evidence confirms;
- what remains a possible explanation;
- which diagnostic actions were performed;
- what information is still missing;
- whether recovery was actually validated.

It is not an autonomous root-cause engine and does not turn pattern matches into confirmed causes.

## Operator workflow

```text
create a case
  -> add evidence
  -> record evidence-backed observations
  -> evaluate a guided playbook
  -> plan and complete diagnostic actions
  -> track possible explanations
  -> generate an L2 escalation package
  -> validate recovery with supporting evidence
  -> export the case summary and handover
```

The current persistent L1-to-L2 workflow includes:

- SQLite-backed cases and local history;
- evidence, observations and diagnostic actions;
- guided investigation playbooks;
- possible-explanation tracking;
- escalation packages and Markdown exports;
- recovery validation;
- complete investigation timeline;
- responsive browser interface;
- tested local Windows launcher.

## What this project demonstrates

INFIOS is portfolio proof for Application Support Engineer, Software Support Engineer, Technical Support Engineer II and Production Support roles.

It demonstrates how I approach support work:

- begin with user and business impact;
- preserve evidence provenance;
- avoid presenting assumptions as facts;
- perform controlled diagnostic actions;
- document missing information and uncertainty;
- prepare escalation-ready technical handovers;
- validate recovery rather than assuming resolution.

## Safety principles

- Sample or sanitized data only.
- No production credentials or unrestricted production logs.
- No automated remediation.
- No SQL writes or production configuration changes.
- Restart or write actions cannot be represented as L1-safe.
- Every factual observation must reference evidence from the same case.
- Possible explanations must reference same-case observations and actions.
- Pattern matching can propose explanations but cannot confirm root cause.
- A confirmed explanation requires explicit operator confirmation and supporting observations.
- A passed recovery validation requires supporting evidence from the same case.

## Quick demo on Windows

From PowerShell in the repository folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\start-infios.ps1
```

The script creates `.venv` when needed, installs the local package, starts INFIOS on `127.0.0.1:8000` and opens the default browser.

Start without opening a browser:

```powershell
.\tools\start-infios.ps1 -NoBrowser
```

Suggested walkthrough:

1. Create a sanitized case.
2. Add evidence and record one evidence-backed observation.
3. Review the guided post-login feature-failure playbook.
4. Create and complete a diagnostic action.
5. Record a possible explanation without confirming it prematurely.
6. Generate an L2 escalation package.
7. Add recovery evidence and validate the outcome.
8. Review the timeline and download the case summary.

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pytest -q
infios serve
```

Open:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## Main API areas

The API provides case, evidence, observation, playbook, diagnostic-action, possible-explanation, escalation, recovery-validation and timeline resources under `/api/cases`.

The browser workflow and generated exports use the same persistent case model. See the local OpenAPI page for the complete endpoint contract.

## Legacy scenario analyzer

The earlier scenario analyzer, CLI, sample incidents, reports, JSON output and local run history remain available for compatibility and focused demonstrations.

Example:

```powershell
python -m app.cli analyze samples/incident-503-dependency.json `
  --out reports/generated/cli-503-demo.md
```

Additional public-safe examples cover access failures, SQL timeouts and log-pattern correlation.

## Exports

The active-case footer provides **Download case summary**. Generated L2 handovers provide a Markdown download next to the copy control.

Exports keep reported information, confirmed observations, possible explanations, diagnostic actions, missing information and recovery validation visibly separated.

## Automated verification

Every pull-request update runs:

- Python tests;
- browser workflow verification with Chromium Playwright;
- responsive navigation checks;
- screenshot, browser-log and trace artifact generation.

Repository-native CI is the default proof loop. Local testing is reserved for Windows-specific launcher validation and controlled usability review.

## Documentation

Additional architecture, workflow, sample-incident and interview material is available under `docs/`.
