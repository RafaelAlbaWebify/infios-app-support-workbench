from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.models import EvidenceItem


SCHEMA_VERSION = 1


class SQLiteEvidenceRepository:
    """Persist case-linked evidence in a local SQLite database."""

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
                CREATE TABLE IF NOT EXISTS evidence_items (
                    evidence_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    observed_at TEXT,
                    collected_at TEXT NOT NULL,
                    certainty TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    schema_version INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_evidence_case_collected
                ON evidence_items(case_id, collected_at ASC, evidence_id ASC)
                """
            )

    def save(self, evidence: EvidenceItem) -> EvidenceItem:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence_items (
                    evidence_id,
                    case_id,
                    evidence_type,
                    source,
                    observed_at,
                    collected_at,
                    certainty,
                    sensitivity,
                    schema_version,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evidence_id) DO UPDATE SET
                    case_id = excluded.case_id,
                    evidence_type = excluded.evidence_type,
                    source = excluded.source,
                    observed_at = excluded.observed_at,
                    collected_at = excluded.collected_at,
                    certainty = excluded.certainty,
                    sensitivity = excluded.sensitivity,
                    schema_version = excluded.schema_version,
                    payload_json = excluded.payload_json
                """,
                (
                    evidence.evidence_id,
                    evidence.case_id,
                    evidence.evidence_type,
                    evidence.source,
                    evidence.observed_at.isoformat() if evidence.observed_at else None,
                    evidence.collected_at.isoformat(),
                    evidence.certainty.value,
                    evidence.sensitivity.value,
                    SCHEMA_VERSION,
                    evidence.model_dump_json(),
                ),
            )
        return evidence

    def get(self, evidence_id: str) -> EvidenceItem | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM evidence_items WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        if row is None:
            return None
        return EvidenceItem.model_validate_json(row["payload_json"])

    def list_for_case(self, case_id: str, limit: int = 200) -> list[EvidenceItem]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM evidence_items
                WHERE case_id = ?
                ORDER BY collected_at ASC, evidence_id ASC
                LIMIT ?
                """,
                (case_id, limit),
            ).fetchall()
        return [EvidenceItem.model_validate_json(row["payload_json"]) for row in rows]
