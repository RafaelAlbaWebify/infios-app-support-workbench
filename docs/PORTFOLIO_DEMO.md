# INFIOS portfolio demonstration

## Goal

Use this walkthrough to demonstrate practical Application Support engineering rather than software-development trivia. The emphasis is evidence quality, operational judgment, escalation readiness, safe lifecycle control and reproducible delivery.

## Suggested introduction

> INFIOS is a local-first Application Support workbench I built to structure incident evidence, guide L1/L2 investigation and connect cases to problem records, known-error guidance, shift handovers, service context and descriptive analytics. It deliberately separates facts from hypotheses and keeps the backend authoritative for lifecycle and safety rules.

## Ten-minute walkthrough

### 1. Start the application

Use the Windows package or repository launcher and open the incident workbench.

Explain that the same application is verified as an editable installation, installed wheel and versioned Windows ZIP.

### 2. Create an incident

Create a sanitized case with a clear application, symptom, affected scope and business impact.

What this proves:

- structured intake;
- local SQLite persistence;
- support-oriented impact capture;
- no requirement to guess a technical cause.

### 3. Add evidence and an observation

Record an exact error or sanitized log excerpt, then convert it into a factual observation that cites the supporting evidence.

What this proves:

- facts remain separate from raw reports;
- evidence relationships are explicit;
- rejected or unsafe inputs are bounded before persistence;
- correlation identifiers can be extracted from sanitized content.

### 4. Review guided checks

Use the playbook guidance and record the actual result of a diagnostic action.

What this proves:

- checks are planned and recorded rather than implied;
- completed actions require results;
- risky operations cannot be mislabeled as routine read-only work.

### 5. Record a possible explanation

Create an explanation supported by observations without prematurely confirming it.

What this proves:

- hypotheses remain distinct from facts;
- confirmation requires explicit operator action and supporting observations;
- recent changes, error codes and dependency links remain context rather than automatic diagnosis.

### 6. Add service context

Link the case explicitly to a catalogue service and review direct dependencies.

What this proves:

- reusable application ownership and dependency context;
- no automatic service assignment;
- topology does not become a causal claim.

### 7. Generate an escalation

Create an L2 handover and download the Markdown package.

What this proves:

- facts, unknowns, completed checks and requested next actions are packaged consistently;
- the receiving team gets evidence rather than an unsupported conclusion.

### 8. Validate recovery

Record the method, result, operator and supporting evidence for recovery validation.

What this proves:

- recovery is not accepted from a status label alone;
- passed validation requires evidence;
- lifecycle transitions remain controlled by backend rules.

### 9. Show related operational surfaces

Open:

- `/problems` for grouped cases, RCA, corrective actions and known-error guidance;
- `/handovers` for immutable shift snapshots;
- `/catalogue` for services, ownership, dependencies and completeness;
- `/analytics` for descriptive metadata trends.

State clearly that these records provide operational context and do not independently prove causality, reliability or individual performance.

### 10. Close with engineering evidence

Show the GitHub Actions history and explain the delivery rule:

- Python tests;
- Chromium Playwright tests;
- Windows bootstrap, persistence and export validation;
- exact-head merge discipline;
- wheel and Windows ZIP package verification.

## Interview discussion points

### Why SQLite?

The target is a single-user local portfolio application. SQLite keeps deployment simple while still proving persistence, schema design, query behavior, restart recovery, bulk records and concurrent reads. Multi-user database hosting is intentionally post-v1.

### Why a modular monolith?

The operational domains are related and deployed together. Separate modules and routers preserve boundaries without adding distributed-system complexity that the local-first use case does not need.

### Why vanilla JavaScript?

The UI needs focused forms, filtering and API calls rather than a large client application. Modular JavaScript keeps the runtime small and makes browser behavior easy to validate with Playwright.

### What is the strongest support-engineering feature?

The evidence chain: raw evidence, factual observations, diagnostic results, possible explanations, escalation and recovery remain linked but distinct. That prevents unsupported RCA language and improves handover quality.

### What would come next in an enterprise version?

Authentication, role-based access, shared deployment, audit retention policy, ticketing integration, external monitoring connectors and a managed database. Those are not required to prove the current local-first support workflow.

## Boundaries during demonstrations

Use only sample or sanitized information. Never enter real credentials, access tokens, session data, recovery codes or confidential production logs.
