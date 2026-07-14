# INFIOS v0.1.0

INFIOS v0.1.0 is the first complete, local-first Application Incident Investigation Workbench release candidate.

It provides a persistent workflow for L1 and L2 Application Support teams to collect evidence, document factual observations, run safe diagnostic checks, track possible explanations, generate escalation handovers, validate recovery and export a complete case record.

## Highlights

- SQLite-backed support cases that survive restart.
- Recent-case dashboard and investigation resume workflow.
- Evidence capture with source, certainty, sensitivity and timestamp metadata.
- Evidence-backed factual observations.
- Guided L1-safe checks with actual-result recording.
- Controlled case lifecycle with invalid-transition protection.
- L2 possible-explanation tracking that keeps hypotheses separate from facts.
- Persistent escalation packages for L2, Development, DBA, Infrastructure, Identity, Vendor or the next shift.
- Evidence-backed recovery validation.
- Chronological incident timeline.
- Downloadable Markdown case summaries and escalation handovers.
- Responsive guided browser interface.
- `infios serve` and Windows `tools/start-infios.ps1` launch paths.

## Safety model

INFIOS does not perform automated remediation or production changes.

- Unknown information remains explicit.
- Observations require supporting evidence from the same case.
- Write or restart operations cannot be represented as L1-safe.
- Possible explanations remain unconfirmed unless an operator explicitly confirms an evidence-supported explanation.
- Passed recovery validation requires supporting evidence.
- Exports preserve the distinction between evidence, observations, actions, possible explanations and missing information.

## Verification

The release candidate is protected by:

- Python domain tests.
- SQLite repository tests.
- FastAPI integration tests.
- Focused Chromium Playwright workflows.
- One continuous create-to-resolved browser lifecycle.
- Real browser verification of Markdown downloads.
- Desktop and 390px responsive checks.
- Runtime JavaScript, console-error and failed-request gates.
- Structural accessibility checks for labels, names, duplicate IDs, skip navigation, live announcements and keyboard focus.

## Installation

On Windows, clone or download the repository and run from PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\start-infios.ps1
```

Alternatively, after Python installation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
infios serve
```

INFIOS opens locally at `http://127.0.0.1:8000`.

## Compatibility

The original scenario analyzer, CLI, JSON output, Markdown reports, sample incidents and local run history remain available.

## Known release constraint

This release must not be tagged or published until the Windows bootstrap smoke test in `docs/release-checklist-v0.1.0.md` is completed.
