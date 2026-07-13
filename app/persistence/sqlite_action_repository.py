from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.models import DiagnosticAction


SCHEMA_VERSION = 1


class SQLiteActionRepository:
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
                CREATE TABLE IF NOT EXISTS diagnostic_actions (
                    action_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    safety_level TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_actions_case_status
                ON diagnostic_actions(case_id, status, action_id)
                """
            )

    def save(self, action: DiagnosticAction) -> DiagnosticAction:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO diagnostic_actions (
                    action_id, case_id, status, safety_level, started_at,
                    completed_at, schema_version, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(action_id) DO UPDATE SET
                    case_id = excluded.case_id,
                    status = excluded.status,
                    safety_level = excluded.safety_level,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json
                """,
                (
                    action.action_id,
                    action.case_id,
                    action.status.value,
                    action.safety_level.value,
                    action.started_at.isoformat() if action.started_at else None,
                    action.completed_at.isoformat() if action.completed_at else None,
                    SCHEMA_VERSION,
                    action.model_dump_json(),
                ),
            )
        return action

    def get(self, action_id: str) -> DiagnosticAction | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM diagnostic_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return None if row is None else DiagnosticAction.model_validate_json(row["payload_json"])

    def list_for_case(self, case_id: str, limit: int = 200) -> list[DiagnosticAction]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM diagnostic_actions
                WHERE case_id = ?
                ORDER BY COALESCE(started_at, ''), action_id
                LIMIT ?
                """,
                (case_id, limit),
            ).fetchall()
        return [DiagnosticAction.model_validate_json(row["payload_json"]) for row in rows]
