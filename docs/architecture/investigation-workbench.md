# INFIOS Investigation Workbench Architecture

## Status

Proposed target architecture for the next major development phase. The existing scenario analyzer remains the verified compatibility baseline until replacement behaviour is covered by tests.

## Product purpose

INFIOS is a local-first Application Incident Investigation Workbench for L1 and L2 support teams. It helps technicians turn fragmented incident information into a traceable investigation containing:

- business impact and affected scope;
- user reports and reproduction results;
- HTTP/API, log, SQL/data, monitoring, dependency, and change evidence;
- confirmed observations separated from possible explanations;
- safe diagnostic actions and their results;
- an evidence-backed timeline;
- role-specific escalation packages;
- recovery validation and cautious RCA notes.

INFIOS does not claim autonomous root-cause determination and does not replace monitoring, log search, API clients, SQL tools, ITSM systems, or engineer judgement.

## Primary users

### L1 technician

Uses a guided workflow with plain language, one recommended action at a time, explicit safety boundaries, and no requirement to understand internal domain terminology.

### L2 Application Support Engineer

Uses structured evidence, observations, possible explanations, diagnostic history, timeline correlation, and escalation/reporting tools.

### Senior reviewer or team lead

Reviews evidence quality, unsupported assumptions, escalation readiness, ownership, recovery validation, and RCA completeness.

## First vertical slice

The first slice covers a post-login application feature failure:

1. Create a case.
2. Record impact and affected scope.
3. Confirm where the login flow succeeds or fails.
4. Add error, screenshot, HTTP/API, log, SQL/data, change, or reproduction evidence.
5. Follow safe guided checks.
6. Record action results.
7. Build an evidence-linked timeline.
8. Generate an L2 escalation package.
9. Persist and reopen the case.

The first slice must work with sample or sanitized data and must not connect to production systems.

## Architecture style

Use a modular monolith. Keep domain and application logic independent from FastAPI, CLI, UI, and persistence frameworks.

```text
app/
  domain/
    cases.py
    evidence.py
    observations.py
    explanations.py
    actions.py
    timeline.py
    escalation.py
  application/
    create_case.py
    add_evidence.py
    analyze_case.py
    start_action.py
    complete_action.py
    generate_escalation.py
  playbooks/
    base.py
    post_login_feature_failure.py
  persistence/
    database.py
    models.py
    repositories.py
  reporting/
    escalation_markdown.py
  api/
    cases.py
    evidence.py
    actions.py
    reports.py
  cli/
  ui/
```

## Core domain concepts

### SupportCase

Represents the complete investigation lifecycle.

Minimum fields:

- case ID;
- title;
- application/service;
- environment;
- status;
- severity;
- business impact;
- affected scope;
- owner;
- created and updated timestamps.

### EvidenceItem

An immutable record of information supplied or collected during the investigation.

Minimum fields:

- evidence ID;
- case ID;
- evidence type;
- source;
- observed and collected timestamps;
- content or structured payload;
- certainty;
- sensitivity classification;
- redaction status;
- attachment reference.

### Observation

A normalized factual statement derived from one or more evidence items. Every observation must reference its supporting evidence IDs.

### PossibleExplanation

An explicitly unconfirmed explanation with supporting observations, contradicting observations, validation actions, and status.

Allowed states:

- proposed;
- supported;
- weakened;
- ruled out;
- confirmed.

Confirmation must be a deliberate evidence-backed action. Keyword matching alone can never confirm root cause.

### DiagnosticAction

A recommended or completed investigation step containing purpose, safety classification, expected result, actual result, conclusion, operator, timestamps, and linked evidence.

Safety levels:

- L1 safe;
- approved runbook required;
- escalation required.

### TimelineEvent

A chronological event linked to evidence, actions, changes, escalation, or recovery validation. Approximate timestamps must remain explicitly approximate.

### EscalationPackage

A generated projection of the current case for a specific recipient such as L2 Application Support, Development, DBA, Infrastructure, Identity, Vendor, or the next shift.

## Playbook contract

A playbook must return structured guidance rather than directly writing a root-cause conclusion.

It should provide:

- applicability reasons;
- evidence already available;
- missing evidence;
- safe diagnostic actions;
- possible explanations;
- escalation criteria;
- safety warnings.

The existing HTTP, access, dependency, SQL, and log scenario knowledge should be migrated into separate playbooks incrementally.

## Persistence

Use SQLite for local-first persistent cases. Introduce schema migrations and repository interfaces. JSON and Markdown remain supported as import/export formats, not the primary mutable case store.

## Compatibility strategy

The current `POST /api/analyze`, CLI analysis command, sample incidents, and generated reports remain available during migration.

Migration rules:

1. Preserve existing tests and behaviour first.
2. Add the new case workflow beside the legacy scenario analyzer.
3. Reuse current samples as compatibility fixtures.
4. Move scenario rules into playbooks only after parity tests exist.
5. Remove legacy paths only in an explicit later milestone.

## Safety boundaries

The first releases must remain:

- local-first;
- sample/sanitized-data only;
- read-only toward external systems;
- credential-free;
- non-remediating;
- explicit about uncertainty;
- conservative with SQL and production actions.

The system must never present a recommendation as authorization to perform a risky action.

## Acceptance principles

A feature is not complete unless automated proof verifies that:

- every observation references evidence;
- reported information is not silently promoted to confirmed fact;
- every action has a safety level;
- completed actions retain results;
- cases survive application restart;
- reports distinguish facts, reported information, explanations, and unknowns;
- no generated output claims confirmed root cause without explicit evidence-backed confirmation.
