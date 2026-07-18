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
- a tested local Windows launcher;
- an installable wheel verified outside the developer checkout;
- a published versioned Windows distribution ZIP.

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

## Published release

The first complete portfolio release is [`v0.1.0`](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/releases/tag/v0.1.0).

Windows package:

[`INFIOS-0.1.0-windows.zip`](https://github.com/RafaelAlbaWebify/infios-app-support-workbench/releases/download/v0.1.0/INFIOS-0.1.0-windows.zip)

After extraction, run `Start-INFIOS.ps1`. The package creates a private Python environment and stores its default SQLite database under the package-local `data` directory.

Requirements:

- Windows 10 or newer;
- Python 3.10 or newer available as `python`;
- internet access during first launch to install Python dependencies.
