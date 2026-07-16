from __future__ import annotations

import sqlite3
from pathlib import Path

from app.known_error_models import KnownErrorRecord


class SQLiteKnownErrorRepository:
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
                "CREATE TABLE IF NOT EXISTS known_errors (known_error_id TEXT PRIMARY KEY, problem_id TEXT NOT NULL, payload_json TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_known_errors_problem_id ON known_errors(problem_id)"
            )

    def save(self, record: KnownErrorRecord) -> KnownErrorRecord:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO known_errors(known_error_id, problem_id, payload_json) VALUES (?, ?, ?) "
                "ON CONFLICT(known_error_id) DO UPDATE SET problem_id=excluded.problem_id, payload_json=excluded.payload_json",
                (record.known_error_id, record.problem_id, record.model_dump_json()),
            )
        return record

    def get(self, known_error_id: str) -> KnownErrorRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM known_errors WHERE known_error_id = ?", (known_error_id,)
            ).fetchone()
        return None if row is None else KnownErrorRecord.model_validate_json(row["payload_json"])

    def list_for_problem(self, problem_id: str, *, limit: int = 200) -> list[KnownErrorRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM known_errors WHERE problem_id = ? ORDER BY rowid DESC LIMIT ?",
                (problem_id, limit),
            ).fetchall()
        return [KnownErrorRecord.model_validate_json(row["payload_json"]) for row in rows]
