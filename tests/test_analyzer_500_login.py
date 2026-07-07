from app.analyzer import analyze_incident
from app.main import load_sample


def test_analyzer_identifies_http_500_login_case() -> None:
    incident = load_sample()
    result = analyze_incident(incident)

    assert result.incident_id == "INFIOS-SAMPLE-500-LOGIN"
    assert result.likely_causes
    assert any("Unhandled application exception" in item for item in result.likely_causes)
    assert any("correlation ID" in item or "Correlation ID" in item for item in result.safe_next_steps)
    assert "confirmed root cause is not yet known" in result.rca_draft


def test_analyzer_keeps_uncertainty_visible() -> None:
    incident = load_sample()
    result = analyze_incident(incident)

    assert result.unknowns
    assert result.missing_evidence
    assert any("Exact failure point" in item for item in result.unknowns)
