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
- `infios serve` local launch command.
- Complete Python, API, SQLite and Chromium Playwright verification.
- Full L1-to-L2-to-recovery browser lifecycle proof.
- Browser runtime-error, console-error and failed-request gate.
- Structural accessibility audit, skip navigation, live announcements and keyboard focus treatment.

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

- Windows bootstrap smoke test on a clean or representative Windows environment.
- Confirm `.venv` creation, package installation, browser opening, persistence across restart and Markdown downloads.
