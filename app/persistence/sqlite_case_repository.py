from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.domain.models import CaseStatus, SupportCase


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
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_support_cases_status_updated_at
                ON support_cases(status, updated_at DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_support_cases_owner_updated_at
                ON support_cases(owner, updated_at DESC)
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
        cases, _ = self.search(limit=limit)
        return cases

    def search(
        self,
        *,
        limit: int = 50,
        query: str | None = None,
        status: CaseStatus | None = None,
        owner: str | None = None,
        sort: str = "updated_desc",
    ) -> tuple[list[SupportCase], int]:
        if limit < 1:
            raise ValueError("limit must be at least 1")

        order_by = {
            "updated_desc": "updated_at DESC, case_id ASC",
            "updated_asc": "updated_at ASC, case_id ASC",
            "created_desc": "json_extract(payload_json, '$.created_at') DESC, case_id ASC",
            "created_asc": "json_extract(payload_json, '$.created_at') ASC, case_id ASC",
        }.get(sort)
        if order_by is None:
            raise ValueError("Unsupported case sort order")

        clauses: list[str] = []
        parameters: list[object] = []
        normalized_query = query.strip().lower() if query else ""
        normalized_owner = owner.strip().lower() if owner else ""

        if normalized_query:
            search_term = f"%{normalized_query}%"
            clauses.append(
                "(LOWER(case_id) LIKE ? OR LOWER(title) LIKE ? OR "
                "LOWER(application) LIKE ? OR LOWER(COALESCE(owner, '')) LIKE ?)"
            )
            parameters.extend([search_term] * 4)

        if status is not None:
            clauses.append("status = ?")
            parameters.append(status.value)

        if normalized_owner == "__unassigned__":
            clauses.append("(owner IS NULL OR TRIM(owner) = '')")
        elif normalized_owner == "__assigned__":
            clauses.append("owner IS NOT NULL AND TRIM(owner) != ''")
        elif normalized_owner:
            clauses.append("LOWER(TRIM(owner)) = ?")
            parameters.append(normalized_owner)

        where_clause = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) AS count FROM support_cases{where_clause}",
                parameters,
            ).fetchone()["count"]
            rows = connection.execute(
                f"""
                SELECT payload_json
                FROM support_cases
                {where_clause}
                ORDER BY {order_by}
                LIMIT ?
                """,
                [*parameters, limit],
            ).fetchall()

        cases = [SupportCase.model_validate_json(row["payload_json"]) for row in rows]
        return cases, int(total)

    def dashboard_counts(self, *, resolved_since: datetime) -> dict[str, int]:
        waiting_statuses = (
            CaseStatus.WAITING_FOR_USER.value,
            CaseStatus.WAITING_FOR_ESCALATION.value,
            CaseStatus.WAITING_FOR_ANOTHER_TEAM.value,
            CaseStatus.BLOCKED.value,
        )
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    SUM(CASE WHEN status NOT IN (?, ?) THEN 1 ELSE 0 END) AS open_cases,
                    SUM(CASE WHEN status IN (?, ?, ?, ?) THEN 1 ELSE 0 END) AS waiting_cases,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS escalated_cases,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS recovery_validation_cases,
                    SUM(CASE WHEN status = ? AND updated_at >= ? THEN 1 ELSE 0 END) AS resolved_since
                FROM support_cases
                """,
                (
                    CaseStatus.RESOLVED.value,
                    CaseStatus.CLOSED.value,
                    *waiting_statuses,
                    CaseStatus.ESCALATED.value,
                    CaseStatus.RECOVERY_VALIDATION.value,
                    CaseStatus.RESOLVED.value,
                    resolved_since.isoformat(),
                ),
            ).fetchone()
        return {key: int(row[key] or 0) for key in row.keys()}
