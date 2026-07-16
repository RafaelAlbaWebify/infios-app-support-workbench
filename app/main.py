from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

from app.analyzer import analyze_incident
from app.api.actions import router as actions_router
from app.api.cases import router as cases_router
from app.api.catalogue import router as catalogue_router
from app.api.database import router as database_router
from app.api.escalations import router as escalations_router
from app.api.evidence import router as evidence_router
from app.api.explanations import router as explanations_router
from app.api.handovers import router as handovers_router
from app.api.lifecycle import router as lifecycle_router
from app.api.observations import router as observations_router
from app.api.playbooks import router as playbooks_router
from app.api.problem_actions import router as problem_actions_router
from app.api.problem_rca import router as problem_rca_router
from app.api.problems import router as problems_router
from app.api.recovery import router as recovery_router
from app.api.summary import router as summary_router
from app.api.timeline import router as timeline_router
from app.api.ui import UI_DIR, router as ui_router
from app.models import AnalysisResult, IncidentInput
from app.report_markdown import render_markdown_report
from app.run_history import list_run_history, save_run_history
from app.version import VERSION

app = FastAPI(
    title="INFIOS Application Support Workbench",
    version=VERSION,
    description="Local-first Application Support workbench for incident evidence, escalation notes, and RCA drafts.",
)
app.mount("/ui/static", StaticFiles(directory=UI_DIR), name="ui-static")
app.include_router(ui_router)
app.include_router(cases_router)
app.include_router(catalogue_router)
app.include_router(handovers_router)
app.include_router(problems_router)
app.include_router(problem_rca_router)
app.include_router(problem_actions_router)
app.include_router(database_router)
app.include_router(evidence_router)
app.include_router(observations_router)
app.include_router(playbooks_router)
app.include_router(actions_router)
app.include_router(timeline_router)
app.include_router(lifecycle_router)
app.include_router(explanations_router)
app.include_router(escalations_router)
app.include_router(recovery_router)
app.include_router(summary_router)

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = ROOT_DIR / "samples"


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "infios-app-support-workbench",
        "version": VERSION,
    }


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
