from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI

from app.analyzer import analyze_incident
from app.models import AnalysisResult, IncidentInput
from app.report_markdown import render_markdown_report

app = FastAPI(
    title="INFIOS Application Support Workbench",
    version="0.1.0",
    description="Local-first Application Support workbench for incident evidence, escalation notes, and RCA drafts.",
)

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


@app.post("/api/analyze", response_model=AnalysisResult)
def analyze(incident: IncidentInput) -> AnalysisResult:
    return analyze_incident(incident)


@app.post("/api/report/markdown")
def markdown_report(incident: IncidentInput) -> dict[str, str]:
    analysis = analyze_incident(incident)
    markdown = render_markdown_report(incident, analysis)
    return {"incident_id": incident.incident_id, "markdown": markdown}


def load_sample(name: str = "incident-500-login.json") -> IncidentInput:
    sample_path = SAMPLES_DIR / name
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    return IncidentInput.model_validate(data)
