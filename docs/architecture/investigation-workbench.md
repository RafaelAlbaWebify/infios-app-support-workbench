# INFIOS Investigation Workbench Architecture

## Status

Implemented backend foundation for the first persistent investigation slice. The original scenario analyzer remains available as a compatibility path while the case-oriented workbench is developed alongside it.

## Product purpose

INFIOS is a local-first Application Incident Investigation Workbench for L1 and L2 support teams. It turns fragmented incident information into a traceable investigation containing business impact, evidence, observations, guided checks, diagnostic actions, possible explanations, escalation packages, recovery validation, timelines, and cautious RCA material.

INFIOS does not claim autonomous root-cause determination and does not replace monitoring, log search, API clients, SQL tools, ITSM systems, or engineer judgement.

## Implemented first vertical slice

The backend now supports a post-login application feature-failure workflow:

1. Create and persist a support case.
2. Control its lifecycle through validated transitions.
3. Add typed evidence with certainty, sensitivity, redaction, and timestamps.
4. Create observations that must reference evidence from the same case.
5. Evaluate a guided post-login failure playbook.
6. Create, start, complete, and persist diagnostic actions with safety classifications.
7. Track possible explanations with supporting and contradicting observations.
8. Prevent confirmation without explicit operator action and supporting observations.
9. Generate and persist an L2 escalation package.
10. Record evidence-backed recovery validation.
11. Generate a complete case summary and chronological timeline.

The slice works with sample or sanitized data and does not connect to production systems.

## Primary users

### L1 technician

Uses a guided workflow with plain language, one recommended action at a time, explicit safety boundaries, and no requirement to understand internal domain terminology.

### L2 Application Support Engineer

Uses structured evidence, observations, possible explanations, diagnostic history, timeline correlation, and escalation/reporting tools.

### Senior reviewer or team lead

Reviews evidence quality, unsupported assumptions, escalation readiness, ownership, recovery validation, and RCA completeness.

## Architecture style

INFIOS uses a modular monolith. Domain and application logic remain independent from FastAPI routes, persistence, CLI, and future UI code.

```text
app/
  domain/
    models.py
    recovery.py
  persistence/
    sqlite_case_repository.py
    sqlite_evidence_repository.py
    sqlite_observation_repository.py
    sqlite_action_repository.py
    sqlite_explanation_repository.py
    sqlite_escalation_repository.py
    sqlite_recovery_repository.py
  playbooks/
    post_login_feature_failure.py
  api/
    cases.py
    lifecycle.py
    evidence.py
    observations.py
    playbooks.py
    actions.py
    explanations.py
    escalations.py
    recovery.py
    timeline.py
    summary.py
```

## Persistence decision

SQLite is the primary mutable case store. Each repository keeps selected searchable columns and the complete validated domain object as JSON.

This hybrid approach provides durable local storage, simple schema boundaries, validated round-trip reconstruction, indexed case-specific listing, and freedom to evolve domain objects before committing to a large ORM model.

JSON and Markdown remain import/export and reporting formats rather than the primary mutable store.

## Evidence and certainty rules

Evidence preserves its source, observed and collected timestamps, certainty, sensitivity, redaction state, and optional attachment reference.

Observations cannot exist without evidence IDs. The API rejects missing or cross-case evidence references.

Possible explanations are separate from observations. They may be proposed, supported, weakened, ruled out, or confirmed. Confirmation requires explicit operator confirmation and at least one supporting observation from the same case. Keyword matching and temporal proximity cannot confirm root cause.

## Diagnostic safety

Diagnostic actions have one of three safety levels:

- L1 safe;
- approved runbook required;
- escalation required.

An action involving a write or restart cannot be represented as L1-safe. A completed action must contain an actual result.

## Escalation projection

The escalation package separates business impact, confirmed observations, reported information, action results, unconfirmed explanations, deliberately confirmed explanations, missing information, the requested receiving-team action, and a safety statement.

The package is persisted so the exact handover can be reviewed later.

## Recovery validation

Recovery validation records the method, result, operator, outcome, supporting evidence, and timestamp. A passed validation requires evidence from the same case.

Case resolution remains a controlled lifecycle action rather than an automatic side effect of one successful test.

## Timeline and summary

The timeline projects case creation, evidence, observations, diagnostic-action starts and completions, escalation generation, and recovery validation.

The case summary aggregates all current investigation objects, playbook guidance, escalation readiness, and the next recommended action for a future L1/L2 interface.

## Compatibility strategy

The current `POST /api/analyze`, CLI analysis command, sample incidents, generated reports, and run history remain available.

Migration rules:

1. Preserve existing tests and behaviour.
2. Build the new case workflow beside the legacy analyzer.
3. Reuse current samples as compatibility fixtures.
4. Move scenario rules into playbooks only after parity tests exist.
5. Remove legacy paths only in an explicit later milestone.

## Safety boundaries

The current release remains local-first, sample or sanitized-data only, read-only toward external systems, credential-free, non-remediating, explicit about uncertainty, and conservative with SQL and production actions.

The system must never present a recommendation as authorization to perform a risky action.

## Automated proof

GitHub Actions verifies the complete legacy and persistent test suite on every pull-request update. The workflow uploads `pytest.log` as a short-lived artifact so failures can be inspected directly.

Tests cover domain invariants, SQLite persistence, case lifecycle, evidence, observations, playbook guidance, diagnostic actions, possible explanations, escalation packages, recovery validation, timeline generation, case-summary readiness, README compatibility, and all legacy analyzer/CLI/report behaviour.

## Next implementation boundary

The backend vertical slice is now complete enough to support UI design. The next phase should define and implement the L1 guided interface over the existing APIs, followed by the L2 investigation view and manual first-time-user usability validation.
