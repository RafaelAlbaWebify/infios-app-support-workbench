# INFIOS Repository-Native Development Workflow

## Goal

Reduce repeated manual PowerShell, ZIP, upload, and interpretation loops. GitHub becomes the shared development and verification environment wherever possible.

## Default workflow

1. Inspect the current repository and the latest commit.
2. Create a focused development branch.
3. Define the behaviour and automated proof before implementation.
4. Make the smallest coherent repository change.
5. Commit the change to the branch.
6. Let GitHub Actions install dependencies and run the automated test suite.
7. Inspect the pull request diff and CI result.
8. Fix failures on the same branch using repository evidence.
9. Request local testing only for behaviour GitHub cannot prove.
10. Merge only after automated checks and required manual proof pass.

## What GitHub should verify

GitHub Actions should progressively cover:

- package installation;
- domain invariants;
- SQLite repository behaviour with temporary databases;
- API integration tests;
- CLI smoke tests;
- database migration tests;
- sample import/export tests;
- report regression tests;
- static checks;
- secret and unsafe-pattern checks;
- deterministic sample workflow tests.

## Current automated persistence proof

The SQLite case repository is tested entirely in GitHub Actions. Tests create isolated temporary databases and verify:

- save and reload without data loss;
- update without duplicate case records;
- ordering by latest update;
- bounded list queries;
- unknown-case behaviour;
- invalid limit rejection.

No user-machine setup, PowerShell script, ZIP export, or manual database inspection is required for this proof.

## What should remain local/manual

Manual testing should be limited to cases that genuinely depend on the user's machine or human judgement:

- first-time-user usability;
- visual layout and accessibility;
- Windows-specific packaging or launcher behaviour;
- file dialogs and local attachment handling;
- browser interaction that cannot be represented by automated UI tests;
- performance on the target PC;
- final acceptance of wording and workflow.

A local test request must include:

- one explicit goal;
- exact starting state;
- minimal steps;
- expected result;
- exact evidence required only when it fails.

## Failure handling

When CI fails:

1. Read the failing job and test output.
2. Identify whether the failure is implementation, test, fixture, dependency, or environment related.
3. Patch only the relevant area.
4. Re-run CI.
5. Do not ask for local testing while repository tests are failing unless the failure is demonstrably environment-specific.

## Branch and pull-request policy

- `main` remains the stable published baseline.
- Each milestone or bounded slice uses its own branch.
- Pull requests begin as drafts for work in progress.
- PR descriptions state goal, scope, risks, tests, compatibility, and remaining manual proof.
- Large architectural changes are split into reviewable milestones.
- Do not mix unrelated cleanup with feature work.

## Compatibility policy

During the investigation-workbench migration:

- preserve the existing sample analyzer;
- preserve current API and CLI behaviour unless an explicit compatibility change is approved;
- add tests before moving scenario behaviour;
- keep old and new paths side by side until parity is demonstrated;
- document deprecations before removal.

## Manual fallback package

A PowerShell audit or patch package is a fallback, not the default. It is appropriate only when:

- the problem exists only in the user's local checkout;
- GitHub does not contain the relevant files;
- Windows-specific behaviour must be inspected;
- local generated artifacts are required;
- credentials or private systems prevent repository-based reproduction.

When used, one grouped script should perform backup, action, verification, report generation, and rollback preparation.

## Definition of done

A milestone is complete only when:

- behaviour is implemented in the repository;
- automated tests prove the agreed acceptance criteria;
- CI passes;
- the pull request diff has been reviewed;
- documentation reflects actual behaviour;
- required local/manual proof is completed;
- known limitations are explicit.
