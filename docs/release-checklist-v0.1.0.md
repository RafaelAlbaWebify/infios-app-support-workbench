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

## Interactive Windows check — required before tag

Run from a fresh interactive PowerShell process in the repository folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\validate-release-windows.ps1
```

The guided validator:

1. Starts INFIOS through the real bootstrap.
2. Opens the local dashboard in the default browser.
3. Creates a public-safe sample case and evidence record.
4. Generates a sample L2 handover.
5. Downloads the case summary and handover into a timestamped Downloads folder.
6. Opens both Markdown files in the configured Windows application.
7. Asks for five yes/no confirmations.
8. Writes `release-validation.md` with the result, environment details, IDs, paths and logs.
9. Opens the evidence folder automatically.

Confirm the behavior that a headless GitHub runner cannot prove:

- [ ] The default browser opens automatically on the interactive Windows desktop.
- [ ] The dashboard is visible and usable in the locally opened browser.
- [ ] Downloaded Markdown files open correctly in the user's configured Windows application.
- [ ] No production credentials or sensitive data are used.
- [ ] The generated `release-validation.md` result is **PASS** and is attached to issue #18.

The underlying bootstrap, installation, startup, persistence, restart and export behavior is already verified on `windows-latest`; this final check is limited to interactive desktop integration and human usability.

## Release actions — only after the interactive check

- [ ] Replace `Unreleased` in `CHANGELOG.md` with the release date.
- [ ] Merge the release-preparation PR.
- [ ] Confirm `main` CI is green at the release commit.
- [ ] Create annotated tag `v0.1.0` at the verified `main` commit.
- [ ] Create GitHub release `INFIOS v0.1.0` from the prepared release notes.
- [ ] Keep the repository public-safe and sample-data-only.

## Rollback

If the interactive Windows check fails:

1. Do not tag or publish the release.
2. Attach the generated report and exact logs from the validation folder.
3. Fix the bootstrap or interactive validator in a separate focused branch.
4. Re-run complete CI, the Windows integration job and the interactive check.
