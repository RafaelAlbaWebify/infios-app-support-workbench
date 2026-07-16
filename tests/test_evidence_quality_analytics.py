from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, SupportCase
from app.evidence_quality_analytics import build_evidence_quality_portfolio_report
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


def test_build_evidence_quality_portfolio_report_counts_metadata_only() -> None:
    cases = [SupportCase(case_id="case-1", title="One", application="ERP"), SupportCase(case_id="case-2", title="Two", application="WMS")]
    evidence = EvidenceItem(
        evidence_id="evidence-1",
        case_id="case-1",
        evidence_type="log_sample",
        source="app.log",
        content="Authorization: Bearer secret-token-value",
        certainty=CertaintyLevel.REPORTED,
        sensitivity=EvidenceSensitivity.INTERNAL,
    )
    report = build_evidence_quality_portfolio_report(cases, {"case-1": [evidence]})

    assert report.total_cases == 2
    assert report.cases_with_evidence == 1
    assert report.cases_without_evidence == 1
    assert report.total_evidence_items == 1
    assert report.evidence_items_requiring_attention == 1
    assert report.cases_requiring_attention == 1
    assert report.certainty_counts == {"reported": 1}
    assert report.evidence_type_counts == {"log_sample": 1}
    assert "not a case-quality score" in report.disclaimer


def test_evidence_quality_api(tmp_path) -> None:
    case_repository = SQLiteCaseRepository(tmp_path / "quality.db")
    evidence_repository = SQLiteEvidenceRepository(tmp_path / "quality.db")
    case_repository.save(SupportCase(case_id="case-1", title="One", application="ERP"))
    evidence_repository.save(
        EvidenceItem(
            case_id="case-1",
            evidence_type="screenshot_reference",
            source="operator",
            content={"reference": "screen-1"},
            certainty=CertaintyLevel.REPORTED,
            sensitivity=EvidenceSensitivity.INTERNAL,
        )
    )
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    try:
        response = TestClient(app).get("/api/analytics/evidence-quality")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] == 1
    assert payload["total_evidence_items"] == 1
    assert "attention_cases" in payload
