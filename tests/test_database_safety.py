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
    repository.save(
        SupportCase(
            case_id=case_id,
            title="Orders API investigation",
            application="Order Management",
        )
    )
    return repository


def test_service_creates_verified_backup_manifest_and_restores_with_audit(tmp_path) -> None:
    database_path = tmp_path / "cases.sqlite3"
    repository = _repository_with_case(database_path)
    service = DatabaseSafetyService(database_path)

    live = service.inspect_live()
    assert live.valid is True
    assert live.integrity == "ok"
    assert live.case_count == 1
    assert len(live.sha256) == 64

    backup = service.create_backup(label="manual test")
    backup_path = service.backup_dir / backup.filename
    manifest_path = backup_path.with_suffix(".json")
    assert backup.valid is True
    assert backup.case_count == 1
    assert backup.filename.startswith("infios-manualtest-")
    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["sha256"] == backup.sha256

    repository.save(
        SupportCase(
            case_id="case-added-later",
            title="Later incident",
            application="Payroll",
        )
    )
    assert service.inspect_live().case_count == 2

    result = service.restore_backup(
        backup.filename,
        performed_by="Application Support",
        reason="Return to verified checkpoint",
    )
    assert result["restored"].case_count == 1
    assert result["pre_restore_backup"].case_count == 2
    assert SQLiteCaseRepository(database_path).get("case-original") is not None
    assert SQLiteCaseRepository(database_path).get("case-added-later") is None

    audit_lines = service.audit_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(audit_lines[-1])
    assert event["performed_by"] == "Application Support"
    assert event["reason"] == "Return to verified checkpoint"
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


def test_database_api_integrity_backup_preview_and_confirmed_restore(tmp_path) -> None:
    repository = _repository_with_case(tmp_path / "api-cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        integrity = client.get("/api/database/integrity")
        assert integrity.status_code == 200
        assert integrity.json()["valid"] is True
        assert integrity.json()["case_count"] == 1

        created = client.post("/api/database/backups", json={"label": "api-checkpoint"})
        assert created.status_code == 201
        backup = created.json()
        assert backup["filename"].startswith("infios-api-checkpoint-")
        assert backup["valid"] is True

        listed = client.get("/api/database/backups")
        assert listed.status_code == 200
        assert listed.json()["count"] == 1

        preview = client.get(f"/api/database/backups/{backup['filename']}/preview")
        assert preview.status_code == 200
        assert preview.json()["sha256"] == backup["sha256"]

        repository.save(
            SupportCase(
                case_id="case-after-api-backup",
                title="Temporary case",
                application="Temporary",
            )
        )

        unconfirmed = client.post(
            "/api/database/restore",
            json={
                "filename": backup["filename"],
                "performed_by": "L1 Support",
                "reason": "Test restore",
                "confirm_restore": False,
            },
        )
        assert unconfirmed.status_code == 422

        restored = client.post(
            "/api/database/restore",
            json={
                "filename": backup["filename"],
                "performed_by": "L1 Support",
                "reason": "Test restore",
                "confirm_restore": True,
            },
        )
        assert restored.status_code == 200
        payload = restored.json()
        assert payload["restored"]["case_count"] == 1
        assert payload["pre_restore_backup"]["case_count"] == 2
        assert repository.get("case-after-api-backup") is None

        traversal = client.get("/api/database/backups/..%2Fcases.sqlite3/preview")
        assert traversal.status_code in {404, 422}
    finally:
        app.dependency_overrides.clear()
