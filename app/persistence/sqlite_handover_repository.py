from __future__ import annotations

import sqlite3
from pathlib import Path

from app.handover_models import ShiftHandover


class SQLiteHandoverRepository:
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
                "CREATE TABLE IF NOT EXISTS shift_handovers ("
                "handover_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload_json TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_shift_handovers_created "
                "ON shift_handovers(created_at DESC, handover_id DESC)"
            )

    def save(self, handover: ShiftHandover) -> ShiftHandover:
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO shift_handovers(handover_id, created_at, payload_json) VALUES (?, ?, ?)",
                    (handover.handover_id, handover.created_at.isoformat(), handover.model_dump_json()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("A shift handover with this identifier already exists.") from exc
        return handover

    def get(self, handover_id: str) -> ShiftHandover | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM shift_handovers WHERE handover_id = ?",
                (handover_id,),
            ).fetchone()
        return None if row is None else ShiftHandover.model_validate_json(row["payload_json"])

    def list_recent(self, limit: int = 50) -> list[ShiftHandover]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM shift_handovers ORDER BY created_at DESC, handover_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ShiftHandover.model_validate_json(row["payload_json"]) for row in rows]
