from __future__ import annotations

import sqlite3
from pathlib import Path

from app.problem_rca_models import ProblemRCAStatement


class SQLiteProblemRCARepository:
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
                "CREATE TABLE IF NOT EXISTS problem_rca_statements "
                "(rca_id TEXT PRIMARY KEY, problem_id TEXT NOT NULL, payload_json TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_problem_rca_problem ON problem_rca_statements(problem_id)"
            )

    def save(self, statement: ProblemRCAStatement) -> ProblemRCAStatement:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO problem_rca_statements(rca_id, problem_id, payload_json) VALUES (?, ?, ?) "
                "ON CONFLICT(rca_id) DO UPDATE SET problem_id=excluded.problem_id, payload_json=excluded.payload_json",
                (statement.rca_id, statement.problem_id, statement.model_dump_json()),
            )
        return statement

    def get(self, rca_id: str) -> ProblemRCAStatement | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM problem_rca_statements WHERE rca_id = ?", (rca_id,)
            ).fetchone()
        return None if row is None else ProblemRCAStatement.model_validate_json(row["payload_json"])

    def list_for_problem(self, problem_id: str) -> list[ProblemRCAStatement]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM problem_rca_statements WHERE problem_id = ? ORDER BY rowid",
                (problem_id,),
            ).fetchall()
        return [ProblemRCAStatement.model_validate_json(row["payload_json"]) for row in rows]
