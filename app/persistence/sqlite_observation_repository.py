from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.models import Observation


SCHEMA_VERSION = 1


class SQLiteObservationRepository:
    """Persist evidence-backed observations in SQLite."""

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
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    certainty TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_observations_case_created
                ON observations(case_id, created_at ASC, observation_id ASC)
                """
            )

    def save(self, observation: Observation) -> Observation:
        payload_json = observation.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO observations (
                    observation_id,
                    case_id,
                    category,
                    certainty,
                    created_at,
                    schema_version,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(observation_id) DO UPDATE SET
                    case_id = excluded.case_id,
                    category = excluded.category,
                    certainty = excluded.certainty,
                    created_at = excluded.created_at,
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json
                """,
                (
                    observation.observation_id,
                    observation.case_id,
                    observation.category,
                    observation.certainty.value,
                    observation.created_at.isoformat(),
                    SCHEMA_VERSION,
                    payload_json,
                ),
            )
        return observation

    def get(self, observation_id: str) -> Observation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM observations WHERE observation_id = ?",
                (observation_id,),
            ).fetchone()
        if row is None:
            return None
        return Observation.model_validate_json(row["payload_json"])

    def list_for_case(self, case_id: str, limit: int = 200) -> list[Observation]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM observations
                WHERE case_id = ?
                ORDER BY created_at ASC, observation_id ASC
                LIMIT ?
                """,
                (case_id, limit),
            ).fetchall()
        return [Observation.model_validate_json(row["payload_json"]) for row in rows]
