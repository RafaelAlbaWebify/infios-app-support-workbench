# INFIOS Demo Commands

This page provides clean terminal commands for demonstrating INFIOS.

Run commands from the repository root after local setup.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pytest -q
```

## Run the API

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Generate an HTTP 503 dependency report

```powershell
python -m app.cli analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md
```

## Generate a SQL evidence report

```powershell
python -m app.cli analyze samples/incident-sql-query-timeout.json --out reports/generated/cli-sql-timeout-demo.md
```

## Generate a log-pattern evidence report

```powershell
python -m app.cli analyze samples/incident-log-pattern-correlation.json --out reports/generated/cli-log-pattern-demo.md
```

## Generate report plus local history

```powershell
python -m app.cli analyze samples/incident-log-pattern-correlation.json --out reports/generated/cli-log-pattern-demo.md --save-history
```

## Use the installed console command

```powershell
infios analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md
```

## Print JSON analysis

```powershell
python -m app.cli analyze samples/incident-403-after-login.json --format json
```

## Safety reminder

All commands use local sample JSON files. They do not connect to production systems, collect credentials, collect production log dumps, modify databases, run SQL queries against real systems, restart services, change permissions, or auto-remediate incidents.
