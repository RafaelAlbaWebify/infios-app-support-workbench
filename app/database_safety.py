from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class DatabaseInspection:
    filename: str
    integrity: str
    valid: bool
    schema_version: int | None
    case_count: int
    size_bytes: int
    sha256: str
    created_at: str


class DatabaseSafetyService:
    """Create, inspect, import, and restore local SQLite backups safely."""

    def __init__(self, database_path: str | Path, backup_dir: str | Path | None = None) -> None:
        self.database_path = Path(database_path)
        self.backup_dir = Path(backup_dir) if backup_dir else self.database_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.backup_dir / "restore-audit.jsonl"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _safe_filename(filename: str) -> str:
        if not filename or Path(filename).name != filename or not filename.endswith(".sqlite3"):
            raise ValueError("Backup filename must be a plain .sqlite3 filename.")
        return filename

    def backup_path(self, filename: str) -> Path:
        return self.backup_dir / self._safe_filename(filename)

    def inspect_path(self, path: Path) -> DatabaseInspection:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path.name)
        try:
            with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
                integrity_row = connection.execute("PRAGMA quick_check").fetchone()
                integrity = str(integrity_row[0]) if integrity_row else "unknown"
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                if "support_cases" not in tables:
                    raise ValueError("Database does not contain the support_cases table.")
                case_count = int(connection.execute("SELECT COUNT(*) FROM support_cases").fetchone()[0])
                version_row = connection.execute("SELECT MAX(schema_version) FROM support_cases").fetchone()
                schema_version = int(version_row[0]) if version_row and version_row[0] is not None else None
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"Invalid SQLite database: {exc}") from exc
        stat = path.stat()
        return DatabaseInspection(
            filename=path.name,
            integrity=integrity,
            valid=integrity.lower() == "ok",
            schema_version=schema_version,
            case_count=case_count,
            size_bytes=stat.st_size,
            sha256=self._sha256(path),
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        )

    def inspect_live(self) -> DatabaseInspection:
        return self.inspect_path(self.database_path)

    def inspect_backup(self, filename: str) -> DatabaseInspection:
        return self.inspect_path(self.backup_path(filename))

    def list_backups(self) -> list[DatabaseInspection]:
        inspections: list[DatabaseInspection] = []
        for path in sorted(self.backup_dir.glob("*.sqlite3"), reverse=True):
            try:
                inspections.append(self.inspect_path(path))
            except (ValueError, sqlite3.DatabaseError):
                continue
        return inspections

    def _write_manifest(self, path: Path, inspection: DatabaseInspection) -> None:
        path.with_suffix(".json").write_text(
            json.dumps(asdict(inspection), indent=2) + "\n",
            encoding="utf-8",
        )

    def create_backup(self, *, label: str = "manual") -> DatabaseInspection:
        if not self.database_path.exists():
            raise FileNotFoundError("Live database does not exist.")
        safe_label = "".join(character for character in label.lower() if character.isalnum() or character == "-")
        safe_label = safe_label.strip("-") or "manual"
        timestamp = self._now().strftime("%Y%m%dT%H%M%SZ")
        destination = self.backup_dir / f"infios-{safe_label}-{timestamp}.sqlite3"
        counter = 1
        while destination.exists():
            destination = self.backup_dir / f"infios-{safe_label}-{timestamp}-{counter}.sqlite3"
            counter += 1
        temporary = destination.with_suffix(".sqlite3.tmp")
        try:
            with sqlite3.connect(self.database_path) as source, sqlite3.connect(temporary) as target:
                source.backup(target)
            inspection = self.inspect_path(temporary)
            if not inspection.valid:
                raise ValueError(f"Backup integrity check failed: {inspection.integrity}")
            os.replace(temporary, destination)
            inspection = self.inspect_path(destination)
            self._write_manifest(destination, inspection)
            return inspection
        finally:
            temporary.unlink(missing_ok=True)

    def import_backup(self, content: bytes, *, original_filename: str) -> DatabaseInspection:
        self._safe_filename(original_filename)
        stem = Path(original_filename).stem
        safe_stem = "".join(character for character in stem.lower() if character.isalnum() or character == "-")
        safe_stem = safe_stem.strip("-")[:40] or "backup"
        timestamp = self._now().strftime("%Y%m%dT%H%M%SZ")
        destination = self.backup_dir / f"infios-imported-{safe_stem}-{timestamp}.sqlite3"
        counter = 1
        while destination.exists():
            destination = self.backup_dir / f"infios-imported-{safe_stem}-{timestamp}-{counter}.sqlite3"
            counter += 1
        temporary = destination.with_suffix(".sqlite3.tmp")
        try:
            temporary.write_bytes(content)
            inspection = self.inspect_path(temporary)
            if not inspection.valid:
                raise ValueError(f"Imported backup integrity check failed: {inspection.integrity}")
            os.replace(temporary, destination)
            inspection = self.inspect_path(destination)
            self._write_manifest(destination, inspection)
            return inspection
        finally:
            temporary.unlink(missing_ok=True)

    def restore_backup(self, filename: str, *, performed_by: str, reason: str) -> dict[str, object]:
        source = self.backup_path(filename)
        preview = self.inspect_path(source)
        if not preview.valid:
            raise ValueError(f"Backup integrity check failed: {preview.integrity}")
        pre_restore = self.create_backup(label="pre-restore")
        temporary = self.database_path.with_suffix(".restore.tmp")
        try:
            with sqlite3.connect(source) as backup_connection, sqlite3.connect(temporary) as target:
                backup_connection.backup(target)
            restored_preview = self.inspect_path(temporary)
            if not restored_preview.valid:
                raise ValueError(f"Restored database integrity check failed: {restored_preview.integrity}")
            os.replace(temporary, self.database_path)
            live = self.inspect_live()
        finally:
            temporary.unlink(missing_ok=True)
        event = {
            "restored_at": self._now().isoformat(),
            "performed_by": performed_by,
            "reason": reason,
            "source_backup": filename,
            "source_sha256": preview.sha256,
            "pre_restore_backup": pre_restore.filename,
            "restored_case_count": live.case_count,
            "restored_schema_version": live.schema_version,
        }
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
        return {"restored": live, "pre_restore_backup": pre_restore, "audit": event}
