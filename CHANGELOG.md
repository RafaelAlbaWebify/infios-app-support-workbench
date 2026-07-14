# Changelog

All notable changes to INFIOS are documented here.

## [0.1.0] - Unreleased

### Added

- Local-first SQLite support-case persistence.
- Controlled incident lifecycle and recovery validation.
- Evidence capture with certainty, sensitivity, redaction and timestamp metadata.
- Evidence-backed factual observations.
- Guided post-login feature-failure playbook.
- L1-safe diagnostic action journal with recorded results.
- Possible-explanation tracking with supporting and contradicting observations.
- Persistent L2 escalation packages and Markdown downloads.
- Complete case-summary Markdown downloads.
- Chronological incident timeline.
- Recent-case dashboard and resume workflow.
- Guided L1 browser interface and first L2 investigation panel.
- Responsive compact case navigation and native disclosure panels.
- Windows PowerShell bootstrap launcher.
- Guided Windows release-validation script with generated evidence report.
- `infios serve` local launch command.
- Complete Python, API, SQLite and Chromium Playwright verification.
- Full L1-to-L2-to-recovery browser lifecycle proof.
- Browser runtime-error, console-error and failed-request gate.
- Structural accessibility audit, skip navigation, live announcements and keyboard focus treatment.
- Real `windows-latest` bootstrap, restart-persistence and export integration gate.

### Safety

- No automated remediation or production-write behavior.
- Unknown information remains explicit.
- Factual observations require same-case evidence.
- Write or restart actions cannot be represented as L1-safe.
- Confirmed explanations require supporting observations and explicit operator confirmation.
- Passed recovery validation requires same-case evidence.
- Exports separate facts, reports, actions, unknowns and possible explanations.

### Compatibility

- Original incident analyzer, CLI, JSON output, Markdown reports, samples and local run history remain available.

### Release gate still pending

- Interactive Windows desktop validation on a representative user machine.
- Confirm the default browser opens visibly, the local dashboard is usable, downloaded Markdown opens in the configured Windows application, and the generated `release-validation.md` result is **PASS**.
- The underlying `.venv` creation, editable installation, local startup, SQLite persistence across restart and Markdown export behavior already pass on `windows-latest`.
