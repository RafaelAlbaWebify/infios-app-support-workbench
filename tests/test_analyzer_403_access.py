from app.analyzer import analyze_incident
from app.main import load_sample
from app.report_markdown import render_markdown_report


def test_analyzer_identifies_http_403_after_login_case() -> None:
    incident = load_sample("incident-403-after-login.json")
    result = analyze_incident(incident)

    assert result.incident_id == "INFIOS-SAMPLE-403-AFTER-LOGIN"
    assert any(finding.category == "Authorization" for finding in result.findings)
    assert any("authenticated" in item.lower() for item in result.likely_causes)
    assert any("known working user" in item for item in result.safe_next_steps)
    assert any("role" in item.lower() or "group" in item.lower() for item in result.missing_evidence)
    assert "confirmed root cause is not yet known" in result.rca_draft


def test_markdown_report_renders_403_access_case() -> None:
    incident = load_sample("incident-403-after-login.json")
    result = analyze_incident(incident)
    report = render_markdown_report(incident, result)

    assert "# INFIOS Incident Report - INFIOS-SAMPLE-403-AFTER-LOGIN" in report
    assert "| HTTP Status | 403 |" in report
    assert "## Likely Causes - Not Confirmed" in report
    assert "Authorization" in report
    assert "Support Boundary" in report

