from __future__ import annotations

import sqlite3
from pathlib import Path

from app.problem_models import ProblemRecord, ProblemStatus


class SQLiteProblemRepository:
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
                "CREATE TABLE IF NOT EXISTS problems (problem_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL)"
            )

    def save(self, problem: ProblemRecord) -> ProblemRecord:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO problems(problem_id, payload_json) VALUES (?, ?) "
                "ON CONFLICT(problem_id) DO UPDATE SET payload_json=excluded.payload_json",
                (problem.problem_id, problem.model_dump_json()),
            )
        return problem

    def get(self, problem_id: str) -> ProblemRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM problems WHERE problem_id = ?", (problem_id,)
            ).fetchone()
        return None if row is None else ProblemRecord.model_validate_json(row["payload_json"])

    def list(self, *, active_only: bool = True) -> list[ProblemRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM problems ORDER BY rowid DESC"
            ).fetchall()
        problems = [ProblemRecord.model_validate_json(row["payload_json"]) for row in rows]
        if not active_only:
            return problems
        return [
            problem
            for problem in problems
            if problem.status not in {ProblemStatus.RESOLVED, ProblemStatus.CLOSED}
        ]
