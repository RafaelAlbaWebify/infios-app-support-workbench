# INFIOS CLI Usage

INFIOS can be used from the terminal as a local Application Support Engineering workbench.

The CLI is useful for portfolio demos because it turns a sample incident JSON file into a support-ready Markdown report without opening Swagger UI.

## Analyze a sample incident

From the repository root:

```powershell
python -m app.cli analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md
```

After installing the project in editable mode:

```powershell
pip install -e ".[dev]"
infios analyze samples/incident-503-dependency.json --out reports/generated/cli-503-demo.md
```

## Print JSON analysis

```powershell
python -m app.cli analyze samples/incident-403-after-login.json --format json
```

## Output

The CLI can produce:

- Markdown report output for support handover and RCA drafting.
- JSON analysis output for automation and future UI integration.

## Safe boundaries

The CLI reads local JSON files only. It does not connect to production systems, collect credentials, modify databases, restart services, change permissions, or auto-remediate incidents.
