# INFIOS 0.1.0

INFIOS 0.1.0 is the first portfolio-ready release of the local-first Application Support Workbench.

## Included

- Persistent incident investigation cases backed by SQLite.
- Evidence, observations, diagnostic actions and evidence-backed possible explanations.
- Sanitized log ingestion, recognized-secret redaction, residual review and correlation-ID extraction.
- Guided investigation playbooks, escalation packages, recovery validation and Markdown exports.
- Service catalogue, explicit case-to-service links, dependency context and completeness reporting.
- Immutable shift handovers.
- Problem records, evidence-backed RCA, corrective actions, audited lifecycle controls and closure readiness.
- Reviewed known-error guidance with draft, publish and retire controls.
- Descriptive operational analytics and configurable activity windows.
- Five responsive operator surfaces with unified navigation and read-only browser filtering.

## Distribution

The release includes `INFIOS-0.1.0-windows.zip`. After extraction, run `Start-INFIOS.ps1`. The package creates a private Python environment and stores its default SQLite database under the package-local `data` directory.

Requirements:

- Windows 10 or newer.
- Python 3.10 or newer available as `python`.
- Internet access during first launch to install Python dependencies.

## Verification

The release scope is covered by:

- Python unit, API, persistence, packaging and resilience tests.
- Chromium Playwright operator-flow, keyboard and narrow-screen tests.
- Windows bootstrap, restart persistence and export smoke tests.
- Outside-checkout wheel installation and HTTP checks for all five browser surfaces.
- Versioned Windows ZIP contract verification.

## Boundaries

INFIOS is a single-user, local-first portfolio application. It does not provide multi-user authentication, automatic remediation, production credential collection, tenant-wide discovery, high availability or external ticketing integrations.

Use only sample or sanitized information. Do not enter credentials, tokens, session data, recovery codes or confidential production logs.
