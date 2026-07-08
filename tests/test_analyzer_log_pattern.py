from app.analyzer import analyze_incident
from app.main import load_sample
from app.report_markdown import render_markdown_report


def test_analyzer_identifies_log_pattern_case() -> None:
    incident = load_sample("incident-log-pattern-correlation.json")
    result = analyze_incident(incident)

    assert result.incident_id == "INFIOS-SAMPLE-LOG-PATTERN"
    assert any(finding.category == "Log pattern" for finding in result.findings)
    assert any(finding.category == "Error clustering" for finding in result.findings)
    assert any("error signature" in item.lower() for item in result.missing_evidence)
    assert any("group log entries" in item.lower() for item in result.safe_next_steps)
    assert any("redact" in item.lower() for item in result.safe_next_steps)
    assert "repeated application log pattern" in result.rca_draft


def test_markdown_report_renders_log_pattern_case() -> None:
    incident = load_sample("incident-log-pattern-correlation.json")
    result = analyze_incident(incident)
    report = render_markdown_report(incident, result)

    assert "# INFIOS Incident Report - INFIOS-SAMPLE-LOG-PATTERN" in report
    assert "| HTTP Status | 500 |" in report
    assert "Log pattern" in report
    assert "Error clustering" in report
    assert "## Support Boundary" in report


def test_log_pattern_case_preserves_redaction_and_uncertainty() -> None:
    incident = load_sample("incident-log-pattern-correlation.json")
    result = analyze_incident(incident)

    assert "confirmed root cause is not yet known" in result.rca_draft
    assert any("secondary noise" in item.lower() for item in result.unknowns)
    assert any("redact tokens" in item.lower() for item in result.safe_next_steps)
    assert "first/last seen timestamps" in result.escalation_note or "first and last seen timestamps" in result.rca_draft
