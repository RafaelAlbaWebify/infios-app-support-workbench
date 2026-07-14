from app.api.ui import UI_DIR


def test_navigation_loads_database_safety_module() -> None:
    navigation = (UI_DIR / "navigation.js").read_text(encoding="utf-8")
    assert "/ui/static/database.js" in navigation


def test_database_safety_ui_exposes_verified_backup_and_confirmed_restore() -> None:
    script = (UI_DIR / "database.js").read_text(encoding="utf-8")

    assert "databasePanel.id = 'database-safety-panel'" in script
    assert 'id="check-database-integrity"' in script
    assert 'id="create-database-backup"' in script
    assert 'id="database-backup-list"' in script
    assert 'id="database-restore-operator"' in script
    assert 'id="database-restore-reason"' in script
    assert 'id="database-restore-confirm"' in script
    assert "'/api/database/integrity'" in script
    assert "'/api/database/backups'" in script
    assert "'/api/database/restore'" in script
    assert "encodeURIComponent(filename)" in script
    assert "confirm_restore" in script
    assert "pre_restore_backup.filename" in script
    assert "window.location.reload()" in script


def test_database_ui_exposes_verified_download_and_validated_import() -> None:
    script = (UI_DIR / "database.js").read_text(encoding="utf-8")

    assert 'id="database-import-file"' in script
    assert 'accept=".sqlite3,application/vnd.sqlite3,application/octet-stream"' in script
    assert 'id="import-database-backup"' in script
    assert 'id="database-import-result"' in script
    assert "file.name.toLowerCase().endsWith('.sqlite3')" in script
    assert "body: await file.arrayBuffer()" in script
    assert "'Content-Type': 'application/octet-stream'" in script
    assert "/api/database/backups/import?filename=" in script
    assert "/api/database/backups/${encodeURIComponent(backup.filename)}/download" in script
    assert "download.download = backup.filename" in script
    assert "Import was not accepted; the live database was not changed." in script


def test_database_panel_is_collapsed_and_requests_data_only_when_opened() -> None:
    script = (UI_DIR / "database.js").read_text(encoding="utf-8")

    assert "document.createElement('details')" in script
    assert "databasePanel.addEventListener('toggle'" in script
    assert "if (databasePanel.open)" in script
    assert "Promise.all([loadDatabaseIntegrity(), loadDatabaseBackups()])" in script
