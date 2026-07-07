from app.analyzer import analyze_incident
from app.main import load_sample
from app.report_markdown import render_markdown_report


def test_analyzer_identifies_sql_timeout_case() -> None:
    incident = load_sample("incident-sql-query-timeout.json")
    result = analyze_incident(incident)

    assert result.incident_id == "INFIOS-SAMPLE-SQL-TIMEOUT"
    assert any(finding.category == "SQL evidence" for finding in result.findings)
    assert any(finding.category == "Database dependency" for finding in result.findings)
    assert any("stored procedure" in item.lower() or "query" in item.lower() for item in result.likely_causes)
    assert any("exact sql error" in item.lower() for item in result.missing_evidence)
    assert any("do not run write queries" in item.lower() for item in result.safe_next_steps)
    assert "SQL/database-dependent operation" in result.rca_draft


def test_markdown_report_renders_sql_timeout_case() -> None:
    incident = load_sample("incident-sql-query-timeout.json")
    result = analyze_incident(incident)
    report = render_markdown_report(incident, result)

    assert "# INFIOS Incident Report - INFIOS-SAMPLE-SQL-TIMEOUT" in report
    assert "| HTTP Status | 500 |" in report
    assert "SQL evidence" in report
    assert "Database dependency" in report
    assert "## Support Boundary" in report


def test_sql_case_preserves_safe_support_boundary() -> None:
    incident = load_sample("incident-sql-query-timeout.json")
    result = analyze_incident(incident)

    assert "confirmed root cause is not yet known" in result.rca_draft
    assert any("read-only" in step.lower() for step in result.safe_next_steps)
    assert any("write queries" in step.lower() for step in result.safe_next_steps)
    assert any("owner approval" in step.lower() for step in result.safe_next_steps)
