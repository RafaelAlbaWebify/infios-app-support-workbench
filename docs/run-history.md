# INFIOS Local Run History

INFIOS can save a local run-history JSON record for each analysis.

This makes the project behave more like a practical support workbench: every analysis can leave an evidence trail with timestamp, incident ID, status, endpoint, finding categories, severity counts, output path, and support boundary.

## CLI usage

Generate a report and save a run-history record:

```powershell
python -m app.cli analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md --save-history
```

Use a custom history directory:

```powershell
python -m app.cli analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md --save-history --history-dir runs/history
```

## API usage

The API includes a history-saving Markdown report endpoint:

```text
POST /api/report/markdown/save
```

It returns:

```text
incident_id
markdown
history_path
```

The API also includes a local history listing endpoint:

```text
GET /api/history
```

## What is stored

A run-history record includes:

- run ID;
- timestamp;
- incident ID;
- title;
- service;
- environment;
- HTTP status;
- endpoint;
- correlation ID;
- source path;
- output path;
- output format;
- finding categories;
- severity counts;
- likely cause count;
- unknown count;
- missing evidence count;
- safe next step count;
- support boundary.

## Safety boundary

Run history is local only. It does not connect to production systems, collect credentials, modify databases, restart services, change permissions, or auto-remediate incidents.

The default runtime history folder is git-ignored:

```text
runs/history/
```
