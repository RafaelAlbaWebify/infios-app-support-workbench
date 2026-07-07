from fastapi.testclient import TestClient

from app.analyzer import analyze_incident
from app.main import app, load_sample
from app.report_markdown import render_markdown_report


client = TestClient(app)


def test_markdown_report_contains_core_sections() -> None:
    incident = load_sample()
    analysis = analyze_incident(incident)
    report = render_markdown_report(incident, analysis)

    assert "# INFIOS Incident Report" in report
    assert "## Evidence Table" in report
    assert "## Likely Causes - Not Confirmed" in report
    assert "## Escalation Note" in report
    assert "## RCA Draft" in report


def test_markdown_report_endpoint() -> None:
    incident = load_sample()
    response = client.post("/api/report/markdown", json=incident.model_dump())

    assert response.status_code == 200
    body = response.json()
    assert body["incident_id"] == "INFIOS-SAMPLE-500-LOGIN"
    assert "HTTP 500" in body["markdown"]
