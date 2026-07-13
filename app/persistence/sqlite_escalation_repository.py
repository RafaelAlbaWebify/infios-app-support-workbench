from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.models import EscalationPackage


SCHEMA_VERSION = 1


class SQLiteEscalationRepository:
    """Persist generated escalation packages for later review and handover."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS escalation_packages (
                    package_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    target_team TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_escalation_packages_case_generated
                ON escalation_packages(case_id, generated_at DESC, package_id ASC)
                """
            )

    def save(self, package: EscalationPackage) -> EscalationPackage:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO escalation_packages (
                    package_id, case_id, target_team, generated_at,
                    schema_version, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(package_id) DO UPDATE SET
                    case_id = excluded.case_id,
                    target_team = excluded.target_team,
                    generated_at = excluded.generated_at,
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json
                """,
                (
                    package.package_id,
                    package.case_id,
                    package.target_team,
                    package.generated_at.isoformat(),
                    SCHEMA_VERSION,
                    package.model_dump_json(),
                ),
            )
        return package

    def get(self, package_id: str) -> EscalationPackage | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM escalation_packages WHERE package_id = ?",
                (package_id,),
            ).fetchone()
        if row is None:
            return None
        return EscalationPackage.model_validate_json(row["payload_json"])

    def list_for_case(self, case_id: str, limit: int = 100) -> list[EscalationPackage]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM escalation_packages
                WHERE case_id = ?
                ORDER BY generated_at DESC, package_id ASC
                LIMIT ?
                """,
                (case_id, limit),
            ).fetchall()
        return [EscalationPackage.model_validate_json(row["payload_json"]) for row in rows]
