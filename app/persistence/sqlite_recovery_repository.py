from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.recovery import RecoveryValidation


SCHEMA_VERSION = 1


class SQLiteRecoveryRepository:
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
                CREATE TABLE IF NOT EXISTS recovery_validations (
                    validation_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    tested_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_recovery_validations_case_tested
                ON recovery_validations(case_id, tested_at DESC, validation_id ASC)
                """
            )

    def save(self, validation: RecoveryValidation) -> RecoveryValidation:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO recovery_validations (
                    validation_id, case_id, outcome, tested_at,
                    schema_version, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(validation_id) DO UPDATE SET
                    case_id = excluded.case_id,
                    outcome = excluded.outcome,
                    tested_at = excluded.tested_at,
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json
                """,
                (
                    validation.validation_id,
                    validation.case_id,
                    validation.outcome.value,
                    validation.tested_at.isoformat(),
                    SCHEMA_VERSION,
                    validation.model_dump_json(),
                ),
            )
        return validation

    def get(self, validation_id: str) -> RecoveryValidation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM recovery_validations WHERE validation_id = ?",
                (validation_id,),
            ).fetchone()
        if row is None:
            return None
        return RecoveryValidation.model_validate_json(row["payload_json"])

    def list_for_case(self, case_id: str, limit: int = 100) -> list[RecoveryValidation]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM recovery_validations
                WHERE case_id = ?
                ORDER BY tested_at DESC, validation_id ASC
                LIMIT ?
                """,
                (case_id, limit),
            ).fetchall()
        return [RecoveryValidation.model_validate_json(row["payload_json"]) for row in rows]
