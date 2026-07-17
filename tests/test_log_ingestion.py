from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.domain.models import SupportCase
from app.log_ingestion import MAX_LOG_BYTES, sanitize_log_text
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


def test_sanitizer_redacts_common_secret_forms_and_preserves_diagnostics() -> None:
    text = (
        "2026-07-15T10:15:00Z request failed correlation_id=req-123\r\n"
        "Authorization: Bearer top-secret-token\r\n"
        "Cookie: session=secret-cookie\r\n"
        "password=hunter2 api_key=key-value\r\n"
        "GET /callback?access_token=query-secret&mode=read\r\n"
        "jwt=eyJabcdefghijk.abcdefghijklmnop.abcdefghijklmnop\r\n"
    )

    result = sanitize_log_text(text)

    assert "top-secret-token" not in result.content
    assert "secret-cookie" not in result.content
    assert "hunter2" not in result.content
    assert "key-value" not in result.content
    assert "query-secret" not in result.content
    assert "eyJabcdefghijk" not in result.content
    assert "correlation_id=req-123" in result.content
    assert "[REDACTED]" in result.content
    assert result.line_count == 7
    assert sum(item.replacements for item in result.findings) == 6


def test_sanitizer_rejects_empty_binary_and_oversized_content() -> None:
    for value, expected in (("", "empty"), ("abc\x00def", "binary"), ("x" * (MAX_LOG_BYTES + 1), "2 MB")):
        try:
            sanitize_log_text(value)
            raise AssertionError("Unsafe log content should be rejected")
        except ValueError as exc:
            assert expected in str(exc)


def test_log_import_api_persists_only_sanitized_evidence(tmp_path) -> None:
    case_repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    evidence_repository = SQLiteEvidenceRepository(tmp_path / "cases.sqlite3")
    support_case = case_repository.save(
        SupportCase(case_id="case-log", title="Import log evidence", application="Orders")
    )
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    client = TestClient(app)

    try:
        response = client.post(
            f"/api/cases/{support_case.case_id}/evidence/import-log",
            json={
                "source": "Approved application log",
                "content": "Authorization: Bearer secret-value\nrequest_id=req-42 status=503",
                "certainty": "technically_confirmed",
                "sensitivity": "internal",
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["redactions"] == {"authorization_header": 1}
        assert payload["evidence"]["redacted"] is True
        assert payload["evidence"]["evidence_type"] == "log_sample"
        assert "secret-value" not in payload["evidence"]["content"]
        assert "request_id=req-42" in payload["evidence"]["content"]

        saved = evidence_repository.get(payload["evidence"]["evidence_id"])
        assert saved is not None
        assert "secret-value" not in str(saved.content)
        assert saved.redacted is True
    finally:
        app.dependency_overrides.clear()


def test_rejected_log_imports_do_not_persist_evidence(tmp_path, monkeypatch) -> None:
    case_repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    evidence_repository = SQLiteEvidenceRepository(tmp_path / "cases.sqlite3")
    support_case = case_repository.save(
        SupportCase(case_id="case-rejected-log", title="Rejected import", application="Orders")
    )
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    client = TestClient(app)

    try:
        binary_response = client.post(
            f"/api/cases/{support_case.case_id}/evidence/import-log",
            json={"source": "Rejected input", "content": "abc\x00def"},
        )
        assert binary_response.status_code == 422
        assert evidence_repository.list_for_case(support_case.case_id) == []

        monkeypatch.setattr("app.log_ingestion.MAX_LOG_BYTES", 4)
        oversized_response = client.post(
            f"/api/cases/{support_case.case_id}/evidence/import-log",
            json={"source": "Rejected input", "content": "12345"},
        )
        assert oversized_response.status_code == 422
        assert evidence_repository.list_for_case(support_case.case_id) == []
    finally:
        app.dependency_overrides.clear()


def test_log_import_requires_existing_case(tmp_path) -> None:
    case_repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    evidence_repository = SQLiteEvidenceRepository(tmp_path / "cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    client = TestClient(app)

    try:
        response = client.post(
            "/api/cases/missing/evidence/import-log",
            json={"source": "log", "content": "status=500"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
