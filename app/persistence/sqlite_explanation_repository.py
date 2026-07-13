from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.models import PossibleExplanation


SCHEMA_VERSION = 1


class SQLiteExplanationRepository:
    """Persist possible explanations while preserving their evidence status."""

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
                CREATE TABLE IF NOT EXISTS possible_explanations (
                    explanation_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_possible_explanations_case
                ON possible_explanations(case_id, explanation_id ASC)
                """
            )

    def save(self, explanation: PossibleExplanation) -> PossibleExplanation:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO possible_explanations (
                    explanation_id, case_id, status, schema_version, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(explanation_id) DO UPDATE SET
                    case_id = excluded.case_id,
                    status = excluded.status,
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json
                """,
                (
                    explanation.explanation_id,
                    explanation.case_id,
                    explanation.status.value,
                    SCHEMA_VERSION,
                    explanation.model_dump_json(),
                ),
            )
        return explanation

    def get(self, explanation_id: str) -> PossibleExplanation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM possible_explanations WHERE explanation_id = ?",
                (explanation_id,),
            ).fetchone()
        if row is None:
            return None
        return PossibleExplanation.model_validate_json(row["payload_json"])

    def list_for_case(self, case_id: str, limit: int = 200) -> list[PossibleExplanation]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM possible_explanations
                WHERE case_id = ?
                ORDER BY explanation_id ASC
                LIMIT ?
                """,
                (case_id, limit),
            ).fetchall()
        return [PossibleExplanation.model_validate_json(row["payload_json"]) for row in rows]
