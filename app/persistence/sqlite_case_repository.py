from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.models import SupportCase


SCHEMA_VERSION = 1


class SQLiteCaseRepository:
    """Persist support cases in a local SQLite database.

    The repository stores the complete validated domain object as JSON while
    keeping selected columns available for filtering and ordering. This keeps
    the first persistence slice small without coupling domain models to SQL.
    """

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
                CREATE TABLE IF NOT EXISTS support_cases (
                    case_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    application TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    owner TEXT,
                    updated_at TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_support_cases_updated_at
                ON support_cases(updated_at DESC)
                """
            )

    def save(self, support_case: SupportCase) -> SupportCase:
        payload_json = support_case.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO support_cases (
                    case_id,
                    title,
                    application,
                    status,
                    severity,
                    owner,
                    updated_at,
                    schema_version,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    title = excluded.title,
                    application = excluded.application,
                    status = excluded.status,
                    severity = excluded.severity,
                    owner = excluded.owner,
                    updated_at = excluded.updated_at,
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json
                """,
                (
                    support_case.case_id,
                    support_case.title,
                    support_case.application,
                    support_case.status.value,
                    support_case.severity,
                    support_case.owner,
                    support_case.updated_at.isoformat(),
                    SCHEMA_VERSION,
                    payload_json,
                ),
            )
        return support_case

    def get(self, case_id: str) -> SupportCase | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM support_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            return None
        return SupportCase.model_validate_json(row["payload_json"])

    def list(self, limit: int = 50) -> list[SupportCase]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM support_cases
                ORDER BY updated_at DESC, case_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [SupportCase.model_validate_json(row["payload_json"]) for row in rows]
