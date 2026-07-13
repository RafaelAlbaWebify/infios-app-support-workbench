# INFIOS Investigation Workbench Architecture

## Status

Active implementation architecture. The existing scenario analyzer remains the compatibility baseline while the persistent investigation workflow is developed alongside it.

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

## Implemented persistent slice

The current branch now supports:

1. creating, listing, and retrieving support cases;
2. adding, listing, and retrieving case-linked evidence;
3. creating evidence-backed observations whose references are validated against the same case;
4. evaluating the first guided post-login feature-failure playbook;
5. creating, starting, completing, listing, and retrieving diagnostic actions;
6. enforcing action safety and recorded-result invariants;
7. persisting these records in local SQLite storage;
8. verifying all workflows through GitHub Actions.

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
5. Convert evidence into traceable observations.
6. Evaluate the post-login feature-failure playbook.
7. Create and execute safe diagnostic actions.
8. Record action results.
9. Build an evidence-linked timeline.
10. Generate an L2 escalation package.
11. Persist and reopen the case.

The first slice must work with sample or sanitized data and must not connect to production systems.

## Architecture style

Use a modular monolith. Keep domain and application logic independent from FastAPI, CLI, UI, and persistence frameworks.

```text
app/
  domain/
  application/
  playbooks/
  persistence/
  reporting/
  api/
  cli/
  ui/
```

## Core domain rules

- Every observation must reference one or more evidence records.
- Evidence references must exist and belong to the same case.
- Reported information must not be silently promoted to technically confirmed information.
- Keyword or pattern matching can propose explanations but can never confirm root cause.
- A confirmed explanation requires explicit operator confirmation and supporting observations.
- Every diagnostic action has a safety level.
- Write or restart actions cannot be classified as L1-safe.
- A completed diagnostic action requires a recorded result.
- A recent change, SQL error, or timeout is evidence, not proof of causation.

## First playbook

`post-login-feature-failure` evaluates stored case context, evidence, and observations. It returns:

- whether the playbook applies and why;
- technically confirmed or reproduced observation IDs;
- missing evidence;
- L1-safe guided checks;
- possible explanations labelled as unconfirmed;
- escalation criteria;
- safety and redaction warnings.

The playbook does not modify systems and does not produce a confirmed root cause.

## Persistence

SQLite is used through repository classes built on Python's standard `sqlite3` module. The current implementation uses separate tables and repositories for:

- support cases;
- evidence;
- observations;
- diagnostic actions.

Validated domain objects are stored as JSON payloads with selected indexed metadata columns. This avoids premature ORM coupling while preserving a clear migration path.

## Compatibility strategy

The current `POST /api/analyze`, CLI analysis command, sample incidents, and generated reports remain available during migration.

Migration rules:

1. Preserve existing tests and behaviour first.
2. Add the new case workflow beside the legacy scenario analyzer.
3. Reuse current samples as compatibility fixtures.
4. Move scenario rules into playbooks only after parity tests exist.
5. Remove legacy paths only in an explicit later milestone.

## Safety boundaries

The first releases remain:

- local-first;
- sample/sanitized-data only;
- read-only toward external systems;
- credential-free;
- non-remediating;
- explicit about uncertainty;
- conservative with SQL and production actions.

The system must never present a recommendation as authorization to perform a risky action.

## Next implementation boundary

The next coherent work is:

1. automatic timeline projections from evidence and diagnostic actions;
2. persistent possible explanations with support/contradiction references;
3. L2 escalation generation based on current stored case state;
4. case status transitions and recovery validation;
5. a simple guided UI only after the backend vertical slice is complete.
