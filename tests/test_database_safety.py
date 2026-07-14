from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.database_safety import DatabaseSafetyService
from app.domain.models import SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def _repository_with_case(path: Path, case_id: str = "case-original") -> SQLiteCaseRepository:
    repository = SQLiteCaseRepository(path)
    repository.save(SupportCase(case_id=case_id, title="Orders API investigation", application="Order Management"))
    return repository


def test_service_creates_verified_backup_manifest_and_restores_with_audit(tmp_path) -> None:
    database_path = tmp_path / "cases.sqlite3"
    repository = _repository_with_case(database_path)
    service = DatabaseSafetyService(database_path)
    live = service.inspect_live()
    assert live.valid is True and live.integrity == "ok" and live.case_count == 1
    assert len(live.sha256) == 64
    backup = service.create_backup(label="manual test")
    backup_path = service.backup_dir / backup.filename
    assert backup.valid is True and backup.case_count == 1
    assert backup.filename.startswith("infios-manualtest-")
    assert json.loads(backup_path.with_suffix(".json").read_text(encoding="utf-8"))["sha256"] == backup.sha256
    repository.save(SupportCase(case_id="case-added-later", title="Later incident", application="Payroll"))
    result = service.restore_backup(backup.filename, performed_by="Application Support", reason="Return to verified checkpoint")
    assert result["restored"].case_count == 1
    assert result["pre_restore_backup"].case_count == 2
    assert SQLiteCaseRepository(database_path).get("case-added-later") is None
    event = json.loads(service.audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert event["source_backup"] == backup.filename
    assert event["pre_restore_backup"].startswith("infios-pre-restore-")


def test_service_rejects_unsafe_or_invalid_backup_files(tmp_path) -> None:
    database_path = tmp_path / "cases.sqlite3"
    _repository_with_case(database_path)
    service = DatabaseSafetyService(database_path)
    try:
        service.inspect_backup("../cases.sqlite3")
        raise AssertionError("Traversal filename should be rejected")
    except ValueError as exc:
        assert "plain .sqlite3 filename" in str(exc)
    invalid = service.backup_dir / "invalid.sqlite3"
    invalid.write_text("not sqlite", encoding="utf-8")
    try:
        service.inspect_backup(invalid.name)
        raise AssertionError("Invalid database should be rejected")
    except ValueError as exc:
        assert "Invalid SQLite database" in str(exc)


def test_portable_import_validates_and_manages_copy(tmp_path) -> None:
    source_path = tmp_path / "source.sqlite3"
    _repository_with_case(source_path, "case-portable")
    service = DatabaseSafetyService(tmp_path / "live.sqlite3")
    imported = service.import_backup(source_path.read_bytes(), original_filename="portable.sqlite3")
    assert imported.valid is True
    assert imported.case_count == 1
    assert imported.filename.startswith("infios-imported-portable-")
    assert service.backup_path(imported.filename).read_bytes() == source_path.read_bytes()
    assert service.backup_path(imported.filename).with_suffix(".json").exists()
    try:
        service.import_backup(b"not sqlite", original_filename="invalid.sqlite3")
        raise AssertionError("Invalid import should fail")
    except ValueError as exc:
        assert "Invalid SQLite database" in str(exc)


def test_database_api_integrity_backup_preview_restore_and_portability(tmp_path) -> None:
    repository = _repository_with_case(tmp_path / "api-cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)
    try:
        integrity = client.get("/api/database/integrity")
        assert integrity.status_code == 200 and integrity.json()["valid"] is True
        created = client.post("/api/database/backups", json={"label": "api-checkpoint"})
        assert created.status_code == 201
        backup = created.json()
        downloaded = client.get(f"/api/database/backups/{backup['filename']}/download")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith("application/vnd.sqlite3")
        imported = client.post(
            "/api/database/backups/import",
            params={"filename": "downloaded.sqlite3"},
            content=downloaded.content,
            headers={"content-type": "application/octet-stream"},
        )
        assert imported.status_code == 201
        assert imported.json()["sha256"] == backup["sha256"]
        invalid_import = client.post(
            "/api/database/backups/import",
            params={"filename": "invalid.sqlite3"},
            content=b"not sqlite",
        )
        assert invalid_import.status_code == 422
        repository.save(SupportCase(case_id="case-after-api-backup", title="Temporary case", application="Temporary"))
        unconfirmed = client.post("/api/database/restore", json={"filename": backup["filename"], "performed_by": "L1 Support", "reason": "Test restore", "confirm_restore": False})
        assert unconfirmed.status_code == 422
        restored = client.post("/api/database/restore", json={"filename": backup["filename"], "performed_by": "L1 Support", "reason": "Test restore", "confirm_restore": True})
        assert restored.status_code == 200
        assert restored.json()["restored"]["case_count"] == 1
        traversal = client.get("/api/database/backups/..%2Fcases.sqlite3/preview")
        assert traversal.status_code in {404, 422}
    finally:
        app.dependency_overrides.clear()
