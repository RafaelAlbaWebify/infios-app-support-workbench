from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.domain.models import (
    CertaintyLevel,
    EvidenceItem,
    EvidenceSensitivity,
    SupportCase,
)
from app.evidence_validation import build_evidence_validation_report
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


def test_report_aggregates_quality_and_secret_issues_without_content() -> None:
    evidence = [
        EvidenceItem(
            evidence_id="evidence-clean",
            case_id="case-1",
            evidence_type="log_sample",
            source="App log",
            observed_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
            content="request_id=req-1 status=200",
            certainty=CertaintyLevel.REPORTED,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-attention",
            case_id="case-1",
            evidence_type="note",
            source="Legacy note",
            content="password=hunter2",
            sensitivity=EvidenceSensitivity.CREDENTIAL_OR_SECRET,
            redacted=False,
        ),
    ]

    report = build_evidence_validation_report(evidence)

    assert report.status == "attention_required"
    assert report.evidence_count == 2
    assert report.attention_required_count == 1
    assert report.issue_counts == {
        "possible_secret_material": 1,
        "credential_evidence_not_redacted": 1,
        "missing_observed_at": 1,
        "unknown_certainty": 1,
    }
    assert report.items[0].status == "clean"
    assert report.items[1].issues == [
        "possible_secret_material",
        "credential_evidence_not_redacted",
        "missing_observed_at",
        "unknown_certainty",
    ]
    assert "hunter2" not in repr(report)


def test_validation_report_endpoint_returns_only_metadata(tmp_path) -> None:
    database = tmp_path / "cases.sqlite3"
    case_repository = SQLiteCaseRepository(database)
    evidence_repository = SQLiteEvidenceRepository(database)
    support_case = case_repository.save(
        SupportCase(case_id="case-validation", title="Validate evidence", application="Orders")
    )
    evidence_repository.save(
        EvidenceItem(
            evidence_id="evidence-risk",
            case_id=support_case.case_id,
            evidence_type="note",
            source="Manual entry",
            content="api_key=secret-value",
        )
    )
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    client = TestClient(app)

    try:
        response = client.get(
            f"/api/cases/{support_case.case_id}/evidence/validation-report"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["case_id"] == support_case.case_id
        assert payload["status"] == "attention_required"
        assert payload["evidence_count"] == 1
        assert payload["attention_required_count"] == 1
        assert payload["items"] == [
            {
                "evidence_id": "evidence-risk",
                "status": "attention_required",
                "issues": [
                    "possible_secret_material",
                    "missing_observed_at",
                    "unknown_certainty",
                ],
                "secret_finding_count": 1,
            }
        ]
        assert "secret-value" not in response.text
    finally:
        app.dependency_overrides.clear()
