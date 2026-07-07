from app.analyzer import analyze_incident
from app.main import load_sample
from app.report_markdown import render_markdown_report


def test_analyzer_identifies_http_503_dependency_case() -> None:
    incident = load_sample("incident-503-dependency.json")
    result = analyze_incident(incident)

    assert result.incident_id == "INFIOS-SAMPLE-503-DEPENDENCY"
    assert any(finding.category == "Dependency" for finding in result.findings)
    assert any(finding.category == "Service availability" for finding in result.findings)
    assert any("downstream" in item.lower() or "dependency" in item.lower() for item in result.likely_causes)
    assert any("dependency health" in item.lower() for item in result.missing_evidence)
    assert any("dependency health" in item.lower() for item in result.safe_next_steps)
    assert "service-availability or dependency failure" in result.rca_draft


def test_markdown_report_renders_503_dependency_case() -> None:
    incident = load_sample("incident-503-dependency.json")
    result = analyze_incident(incident)
    report = render_markdown_report(incident, result)

    assert "# INFIOS Incident Report - INFIOS-SAMPLE-503-DEPENDENCY" in report
    assert "| HTTP Status | 503 |" in report
    assert "Dependency" in report
    assert "Service availability" in report
    assert "## Support Boundary" in report


def test_503_dependency_case_keeps_application_and_dependency_boundary_separate() -> None:
    incident = load_sample("incident-503-dependency.json")
    result = analyze_incident(incident)

    assert any("do not assume the frontend service itself is the root cause" in step.lower() for step in result.safe_next_steps)
    assert any("which dependency is failing" in item.lower() for item in result.unknowns)
    assert "confirmed root cause is not yet known" in result.rca_draft
