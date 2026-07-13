# INFIOS Repository-Native Development Workflow

## Goal

Reduce repeated manual PowerShell, ZIP, upload, and interpretation loops. GitHub is the shared development and verification environment wherever possible.

## Default workflow

1. Inspect the current repository and latest commit.
2. Create or continue a focused development branch.
3. Define behaviour and automated proof before implementation.
4. Make the smallest coherent repository change.
5. Commit the change to the branch.
6. Let GitHub Actions install dependencies and run the complete test suite.
7. Inspect the pull request diff and CI result.
8. Read failing job output and patch the branch directly.
9. Request local testing only for behaviour GitHub cannot prove.
10. Merge only after automated checks and required manual proof pass.

## Verified use of this workflow

During the guided playbook and diagnostic-action milestone, CI found an API-boundary defect in unsafe-action validation. The failure was diagnosed from GitHub Actions, corrected in the repository, and verified again without asking for local reproduction. This is the expected development loop.

## What GitHub verifies

GitHub Actions progressively covers:

- package installation;
- domain invariant tests;
- API integration tests;
- SQLite round-trip and isolation tests;
- legacy endpoint compatibility;
- playbook behaviour;
- action safety and lifecycle rules;
- report regression tests;
- deterministic sample workflows.

## What remains local/manual

Manual testing is limited to behaviour that genuinely depends on the user's machine or human judgement:

- first-time-user usability;
- visual layout and accessibility;
- Windows-specific packaging or launcher behaviour;
- file dialogs and local attachment handling;
- browser interaction not represented by automated UI tests;
- performance on the target PC;
- final acceptance of wording and workflow.

A local test request must include one explicit goal, exact starting state, minimal steps, expected result, and evidence only when it fails.

## Failure handling

When CI fails:

1. Read the failing job and test output.
2. Classify the failure as implementation, API boundary, test, fixture, dependency, or environment related.
3. Patch only the relevant area.
4. Re-run CI.
5. Do not request local testing while repository tests are failing unless the failure is demonstrably environment-specific.

## Branch and pull-request policy

- `main` remains the stable published baseline.
- Each milestone or bounded slice uses its own branch.
- Pull requests begin as drafts for work in progress.
- PR descriptions state goal, scope, risks, tests, compatibility, and remaining manual proof.
- Large architectural changes are split into reviewable milestones.
- Unrelated cleanup is not mixed with feature work.

## Compatibility policy

During the investigation-workbench migration:

- preserve the existing sample analyzer;
- preserve current API and CLI behaviour unless an explicit compatibility change is approved;
- add tests before moving scenario behaviour;
- keep old and new paths side by side until parity is demonstrated;
- document deprecations before removal.

## Manual fallback package

A PowerShell audit or patch package is a fallback, not the default. It is appropriate only when the problem exists only in the user's local checkout, GitHub lacks relevant files, Windows-specific behaviour must be inspected, local generated artifacts are required, or credentials/private systems prevent repository reproduction.

When used, one grouped script should perform backup, action, verification, report generation, and rollback preparation.

## Definition of done

A milestone is complete only when behaviour is implemented in the repository, automated tests prove the agreed acceptance criteria, CI passes, the pull request diff is reviewed, documentation reflects actual behaviour, required local proof is complete, and known limitations are explicit.
