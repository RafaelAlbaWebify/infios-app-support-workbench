from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.domain.models import EvidenceItem, SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.secret_scanning import scan_evidence_content


def test_scanner_reports_categories_locations_and_counts_without_values() -> None:
    findings = scan_evidence_content(
        {
            "headers": "Authorization: Bearer top-secret\nCookie: sid=abc",
            "request": {"url": "https://example.test?api_key=key-123"},
            "private": "-----BEGIN PRIVATE KEY-----",
        }
    )

    assert [(item.kind, item.location, item.occurrences) for item in findings] == [
        ("authorization_header", "content.headers", 1),
        ("cookie_header", "content.headers", 1),
        ("url_secret", "content.request.url", 1),
        ("private_key", "content.private", 1),
    ]
    assert "top-secret" not in repr(findings)
    assert "key-123" not in repr(findings)


def test_scanner_treats_redacted_material_as_clean() -> None:
    findings = scan_evidence_content(
        "Authorization: [REDACTED]\npassword=[REDACTED]\napi_key=[REDACTED]"
    )
    assert findings == []


def test_secret_scan_endpoint_is_read_only_and_does_not_return_secret_values(tmp_path) -> None:
    database = tmp_path / "cases.sqlite3"
    case_repository = SQLiteCaseRepository(database)
    evidence_repository = SQLiteEvidenceRepository(database)
    support_case = case_repository.save(
        SupportCase(case_id="case-secret-scan", title="Inspect evidence", application="Orders")
    )
    evidence = evidence_repository.save(
        EvidenceItem(
            case_id=support_case.case_id,
            evidence_type="log_sample",
            source="Legacy import",
            content="password=hunter2\nrequest_id=req-7",
            redacted=False,
        )
    )
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    client = TestClient(app)

    try:
        response = client.get(
            f"/api/cases/{support_case.case_id}/evidence/{evidence.evidence_id}/secret-scan"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload == {
            "evidence_id": evidence.evidence_id,
            "status": "attention_required",
            "finding_count": 1,
            "findings": [
                {"kind": "named_secret", "location": "content", "occurrences": 1}
            ],
        }
        assert "hunter2" not in response.text
        persisted = evidence_repository.get(evidence.evidence_id)
        assert persisted is not None
        assert persisted.content == "password=hunter2\nrequest_id=req-7"
    finally:
        app.dependency_overrides.clear()
