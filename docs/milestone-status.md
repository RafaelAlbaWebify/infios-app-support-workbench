# INFIOS Milestone Status

## Current status

INFIOS is an API-first Application Support Engineering workbench with a CLI runner and local run history.

| Milestone | Scenario | Status | Proof |
|---|---|---|---|
| M1 | HTTP 500 after login | Published | Sample incident, analyzer rules, report, tests |
| M2 | HTTP 403 after login | Published | Sample incident, authorization rules, report, tests |
| M2.1 | Cleanup and interview proof | Published | Cleaner report wording, quality tests, interview notes, milestone status |
| M3 | HTTP 503 dependency unavailable | Published | Sample incident, dependency/service-health rules, report, tests |
| M4 | CLI runner | Published | `python -m app.cli`, console script entry point, CLI tests, generated CLI demo report |
| M5 | Local run history | Published | Timestamped JSON run records, CLI history flag, API history endpoint, tests, generated history demo |

## Current capabilities

- FastAPI backend.
- CLI runner.
- Local run-history records.
- Pydantic incident and analysis models.
- Sample incident loading.
- Evidence-first analyzer rules.
- Markdown report generation.
- JSON analysis output from CLI.
- GitHub Actions CI.
- Local pytest suite.
- Sample reports for portfolio review.
- Interview notes explaining the support reasoning.
- HTTP 500 application failure triage.
- HTTP 403 access/authorization triage.
- HTTP 503 dependency/service-health triage.

## Not yet included

- Frontend dashboard.
- Real log parser.
- Real production integrations.
- SQL evidence scenario.
- Saved incident archive UI.
- Search/filter over history records.

## Next recommended milestone

M6 should add a SQL evidence scenario.

That would show stronger Application Support Engineer readiness around data-dependent applications without pretending to be a DBA: query timeout, missing row, stale reference data, failed stored procedure, or SQL connection evidence.
