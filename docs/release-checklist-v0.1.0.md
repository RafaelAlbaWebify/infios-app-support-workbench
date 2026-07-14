# INFIOS v0.1.0 Release Checklist

## Automated verification

- [x] Python/domain/API/SQLite suite passes in GitHub Actions.
- [x] Chromium Playwright suite passes in GitHub Actions.
- [x] Full L1-to-L2-to-recovery browser journey passes.
- [x] Case-summary and escalation Markdown downloads are verified in Chromium.
- [x] No uncaught JavaScript exceptions during the complete workflow.
- [x] No browser console errors during the complete workflow.
- [x] No failed same-origin application requests during the complete workflow.
- [x] Dashboard and active case have no duplicate IDs.
- [x] Visible form controls are labeled.
- [x] Visible interactive controls have accessible names.
- [x] Skip navigation and keyboard focus visibility pass.
- [x] Desktop and 390px mobile layouts have no horizontal page overflow.
- [x] Long escalation Markdown wraps inside the case panel.
- [x] `windows-latest` executes the real PowerShell bootstrap.
- [x] Windows bootstrap creates `.venv` when absent.
- [x] Windows editable installation completes without manual repair.
- [x] INFIOS starts and reports version `0.1.0` on Windows.
- [x] A case is created and persisted to an explicit SQLite path on Windows.
- [x] The Windows server stops and restarts through the bootstrap.
- [x] The saved case reappears after the Windows restart.
- [x] Case-summary Markdown downloads and contains the expected case.
- [x] L2 escalation Markdown downloads and contains the expected request.
- [x] Windows bootstrap evidence is uploaded as a CI artifact.
- [x] The guided interactive validation script parses successfully on `windows-latest`.
- [x] The validator generates an upload-ready ZIP archive automatically.

## Interactive Windows validation

Completed on July 14, 2026 using the guided validation workflow.

- [x] The default browser opened automatically on the interactive Windows desktop.
- [x] The dashboard was visible and usable in the locally opened browser.
- [x] The case-summary Markdown opened correctly in the configured Windows application.
- [x] The L2 handover Markdown opened correctly in the configured Windows application.
- [x] Only sample/public-safe data was used.
- [x] The generated `release-validation.md` result was **PASS**.
- [x] The evidence archive was reviewed and summarized in issue #18.

Validated environment:

- Windows: Microsoft Windows NT 10.0.26100.0.
- PowerShell: 5.1.26100.8655.
- INFIOS health version: `0.1.0`.
- Sample case: `case-e24daffa67ad`.
- Sample evidence: `evidence-7291085a0eae`.
- Sample escalation: `escalation-169869cdc037`.

## Release actions

- [x] Replace `Unreleased` in `CHANGELOG.md` with the release date.
- [ ] Merge the release-preparation PR.
- [ ] Confirm `main` CI is green at the release commit.
- [ ] Create annotated tag `v0.1.0` at the verified `main` commit.
- [ ] Create GitHub release `INFIOS v0.1.0` from the prepared release notes.
- [x] Keep the repository public-safe and sample-data-only.

## Rollback

If a release action fails:

1. Do not move the `v0.1.0` tag to an unverified commit.
2. Record the exact failing check or publication step.
3. Fix the defect in a focused branch.
4. Re-run complete CI before retrying the release action.
