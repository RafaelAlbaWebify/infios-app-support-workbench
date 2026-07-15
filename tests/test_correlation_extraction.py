from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.correlation_extraction import extract_correlation_identifiers
from app.domain.models import SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


def test_extracts_supported_identifiers_and_deduplicates_in_pattern_order() -> None:
    text = (
        "correlation_id=req-123 request-id=abc.456\n"
        "X-Correlation-ID: req-123\n"
        "trace_id=4bf92f3577b34da6a3ce929d0e0e4736\n"
        "traceparent=00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01\n"
    )

    identifiers = extract_correlation_identifiers(text)

    assert [(item.kind, item.value) for item in identifiers] == [
        ("correlation_id", "req-123"),
        ("request_id", "abc.456"),
        ("trace_id", "4bf92f3577b34da6a3ce929d0e0e4736"),
        ("traceparent", "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"),
    ]


def test_ignores_redaction_markers_and_unlabelled_values() -> None:
    text = "request_id=[REDACTED] random=req-unsafe correlation-id=valid-1"
    identifiers = extract_correlation_identifiers(text)
    assert [(item.kind, item.value) for item in identifiers] == [("correlation_id", "valid-1")]


def test_log_import_returns_identifiers_from_sanitized_content(tmp_path) -> None:
    case_repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    evidence_repository = SQLiteEvidenceRepository(tmp_path / "cases.sqlite3")
    support_case = case_repository.save(
        SupportCase(case_id="case-correlation", title="Trace request", application="Orders")
    )
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    client = TestClient(app)

    try:
        response = client.post(
            f"/api/cases/{support_case.case_id}/evidence/import-log",
            json={
                "source": "Application log",
                "content": (
                    "Authorization: Bearer secret-token\n"
                    "x-request-id: req-42 correlation_id=corr-7 status=503"
                ),
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["correlation_identifiers"] == [
            {"kind": "correlation_id", "value": "corr-7"},
            {"kind": "request_id", "value": "req-42"},
        ]
        assert "secret-token" not in payload["evidence"]["content"]
        assert "2 correlation identifier(s)" in payload["evidence"]["notes"]
    finally:
        app.dependency_overrides.clear()
