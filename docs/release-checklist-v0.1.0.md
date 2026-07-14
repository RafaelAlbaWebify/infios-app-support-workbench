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

## Windows smoke test — required before tag

Run from a fresh PowerShell process in the repository folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\start-infios.ps1
```

Confirm:

- [ ] `.venv` is created when absent.
- [ ] Package installation completes without manual repair.
- [ ] INFIOS starts on `http://127.0.0.1:8000`.
- [ ] The default browser opens automatically.
- [ ] A case can be created and saved.
- [ ] INFIOS can be stopped and restarted.
- [ ] The saved case reappears after restart.
- [ ] Case-summary Markdown downloads successfully.
- [ ] L2 escalation Markdown downloads successfully.
- [ ] Downloaded files open correctly on Windows.
- [ ] No production credentials or sensitive data were used.

## Release actions — only after the smoke test

- [ ] Replace `Unreleased` in `CHANGELOG.md` with the release date.
- [ ] Merge the release-preparation PR.
- [ ] Confirm `main` CI is green at the release commit.
- [ ] Create annotated tag `v0.1.0` at the verified `main` commit.
- [ ] Create GitHub release `INFIOS v0.1.0` from the prepared release notes.
- [ ] Keep the repository public-safe and sample-data-only.

## Rollback

If the Windows smoke test fails:

1. Do not tag or publish the release.
2. Record the exact PowerShell output and failing step.
3. Fix the bootstrap in a separate focused branch.
4. Re-run complete CI and the Windows smoke test.
