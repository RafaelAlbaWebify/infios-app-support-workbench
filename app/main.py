from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

from app.analyzer import analyze_incident
from app.api.cases import router as cases_router
from app.api.evidence import router as evidence_router
from app.api.observations import router as observations_router
from app.models import AnalysisResult, IncidentInput
from app.report_markdown import render_markdown_report
from app.run_history import list_run_history, save_run_history

app = FastAPI(
    title="INFIOS Application Support Workbench",
    version="0.1.0",
    description="Local-first Application Support workbench for incident evidence, escalation notes, and RCA drafts.",
)
app.include_router(cases_router)
app.include_router(evidence_router)
app.include_router(observations_router)

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT_DIR / "samples"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "infios-app-support-workbench"}


@app.get("/api/samples")
def samples() -> dict[str, list[str]]:
    if not SAMPLES_DIR.exists():
        return {"samples": []}
    return {"samples": sorted(path.name for path in SAMPLES_DIR.glob("*.json"))}


@app.get("/api/history")
def history() -> dict[str, object]:
    records = list_run_history()
    return {"history": records, "count": len(records)}


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(incident: IncidentInput) -> AnalysisResult:
    return analyze_incident(incident)


@app.post("/api/report/markdown")
def markdown_report(incident: IncidentInput) -> dict[str, str]:
    analysis = analyze_incident(incident)
    markdown = render_markdown_report(incident, analysis)
    return {"incident_id": incident.incident_id, "markdown": markdown}


@app.post("/api/report/markdown/save")
def markdown_report_with_history(incident: IncidentInput) -> dict[str, str]:
    analysis = analyze_incident(incident)
    markdown = render_markdown_report(incident, analysis)
    history_path = save_run_history(
        incident,
        analysis,
        source_path="api:/api/report/markdown/save",
        output_format="markdown",
    )
    return {
        "incident_id": incident.incident_id,
        "markdown": markdown,
        "history_path": str(history_path),
    }


def load_sample(name: str = "incident-500-login.json") -> IncidentInput:
    sample_path = SAMPLES_DIR / name
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    return IncidentInput.model_validate(data)
