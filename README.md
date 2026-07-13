# INFIOS - Application Support Workbench

[![INFIOS CI](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/actions/workflows/ci.yml)

**Incident Flow & Information Operations Support**

INFIOS is a local-first Application Support Engineering workbench. It helps support teams turn fragmented application incidents into structured cases containing evidence, traceable observations, guided checks, diagnostic actions, escalation context, and cautious RCA material.

## Current development status

The persistent investigation workflow is being developed on the draft pull-request branch `architecture/investigation-workbench`. The `main` branch remains the published compatibility baseline until the new slice is reviewed and merged.

## Purpose

This repository is designed both as portfolio proof for Application Support Engineer, Software Support Engineer, Technical Support Engineer II, and Production Support Engineer roles, and as the foundation of a practical incident-investigation tool for L1 and L2 support teams.

INFIOS is not an autonomous root-cause engine. It preserves the distinction between reported information, technically confirmed observations, possible explanations, completed diagnostic actions, and unresolved unknowns.

## Persistent investigation workflow

```text
Create case
→ add evidence
→ create evidence-backed observations
→ evaluate a guided playbook
→ create/start/complete diagnostic actions
→ reopen and review the stored investigation
```

### Case endpoints

- `POST /api/cases`
- `GET /api/cases`
- `GET /api/cases/{case_id}`

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

## Safety principles

- Sample or sanitized data only.
- No production credentials or unrestricted production logs.
- No automated remediation.
- No SQL writes or production configuration changes.
- Restart/write actions cannot be represented as L1-safe.
- Every factual observation must reference evidence from the same case.
- Pattern matching can propose explanations but cannot confirm root cause.

## Legacy compatibility

The original scenario analyzer, CLI, sample incidents, Markdown reports, JSON output, and local run history remain available while the persistent workbench is developed alongside them.

## Development verification

GitHub Actions installs the package and runs the complete automated test suite for every pull-request update. Repository-native CI is the default proof loop; local PowerShell and manual testing are reserved for Windows-specific packaging and later usability/visual validation.
