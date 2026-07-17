# INFIOS — Application Support Workbench

[![INFIOS CI](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml)

**Incident Flow & Information Operations Support**

INFIOS is a local-first Application Support investigation and operations workbench. It turns fragmented incident information into structured, evidence-backed cases and connects those cases to problem management, known-error guidance, shift handovers, service context and descriptive operational analytics.

It is designed as portfolio proof for Application Support Engineer, Software Support Engineer, Technical Support Engineer II, Production Support and SaaS Support roles.

## What INFIOS does

The current persistent workflow supports:

- SQLite-backed incident cases and local history;
- evidence, observations and diagnostic actions;
- guided investigation playbooks;
- evidence-backed possible explanations;
- sanitized log ingestion and residual-secret review;
- correlation-ID extraction from sanitized evidence;
- L2 escalation packages and Markdown exports;
- recovery validation with supporting evidence;
- complete investigation timelines;
- reusable service and dependency catalogue records;
- explicit case-to-service links and direct dependency context;
- catalogue completeness reporting;
- immutable operator-authored shift handovers;
- problem records, RCA statements and corrective actions;
- advisory problem closure-readiness reporting;
- audited problem lifecycle changes and explicit safe closure;
- reviewed known-error guidance with draft, publish and retire controls;
- descriptive operational analytics and configurable activity windows;
- responsive browser interfaces with read-only list filtering;
- a tested local Windows launcher.

## Operator surfaces

| Surface | Purpose |
|---|---|
| `/` | Incident investigation workbench |
| `/problems` | Problem management, corrective actions and known errors |
| `/handovers` | Immutable shift handover snapshots |
| `/catalogue` | Service catalogue, dependencies and completeness context |
| `/analytics` | Descriptive operational analytics |

The browser surfaces share unified navigation and preserve the same interpretation boundaries as the backend.

## Investigation workflow

```text
create a case
  -> add or import sanitized evidence
  -> record evidence-backed observations
  -> evaluate a guided playbook
  -> plan and complete diagnostic actions
  -> track possible explanations
  -> link explicit service context when appropriate
  -> generate an L2 escalation package
  -> validate recovery with supporting evidence
  -> export the case summary or handover
```

Related cases can then be explicitly grouped into a problem record, reviewed through evidence-backed RCA, tracked with corrective actions, documented through known-error guidance and moved through an audited lifecycle.

## Safety and interpretation principles

- Sample or sanitized data only.
- No production credentials, MFA codes, recovery codes, tokens or session cookies.
- No automated remediation.
- No SQL writes or production configuration changes.
- Restart or write actions cannot be represented as L1-safe or read-only.
- Every factual observation must reference evidence from the same case.
- Possible explanations must reference same-case observations and actions.
- Pattern matches, failure codes and recent changes are evidence or context, not automatic diagnosis.
- A confirmed explanation requires explicit operator confirmation and supporting observations.
- A passed recovery validation requires supporting evidence from the same case.
- Catalogue links and dependencies are operational context, not proof of failure or causation.
- Problem grouping and known-error records do not independently prove shared root cause or permanent resolution.
- Analytics describe stored metadata and do not measure operator performance, service quality, reliability or causality.
- Browser filters operate only on loaded records and never change stored data.
- Backend validation remains authoritative for all lifecycle and safety rules.

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
3. Review a guided playbook.
4. Create and complete a diagnostic action.
5. Record a possible explanation without confirming it prematurely.
6. Link explicit service context.
7. Generate an L2 escalation package.
8. Add recovery evidence and validate the outcome.
9. Review the timeline and download the case summary.
10. Review the related problem, handover, catalogue and analytics surfaces.

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

The API provides resources for:

- cases, evidence, observations and diagnostic actions;
- playbooks, possible explanations and recovery validation;
- escalation packages, timelines and exports;
- service catalogue entries, dependencies and case links;
- shift handovers;
- problems, RCA statements, corrective actions and known errors;
- closure readiness and lifecycle history;
- operational analytics.

The browser workflow and generated exports use the same persistent models and backend validation. The local OpenAPI page is the complete endpoint contract.

## Demo Commands

The earlier scenario analyzer, CLI, sample incidents, JSON output and local run history remain available for focused demonstrations.

```powershell
python -m app.cli analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md
python -m app.cli analyze samples/incident-sql-query-timeout.json --out reports/generated/cli-sql-timeout-demo.md
```

## Demo Reports

Generated examples under `reports/` demonstrate incident summaries, user impact, evidence tables, unconfirmed possible causes, missing evidence, safe next steps, escalation notes and cautious RCA material.

Examples include:

- `reports/sample-500-login-report.md`;
- `reports/sample-403-access-report.md`;
- `reports/sample-503-dependency-report.md`;
- `reports/sample-sql-query-timeout-report.md`;
- `reports/sample-log-pattern-report.md`.

## Automated verification

Every pull-request update runs:

- Python tests;
- Chromium Playwright browser tests;
- responsive navigation and operator-flow checks;
- Windows bootstrap, persistence and export smoke tests;
- screenshot, browser-log and trace artifact generation.

A change is considered complete only after all required jobs pass on the exact pull-request head and that head is merged.

## Project status

The working estimate is **82% complete**, with **18% remaining** for the defined portfolio-ready v1 scope. The remaining work is concentrated in repeatable Windows packaging, security/performance hardening, final cross-surface usability validation and release verification.

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the weighted calculation, completed capability inventory and remaining v1 work.

## Documentation

Additional architecture, workflow, sample-incident and interview material is available under `docs/`.
