from __future__ import annotations

import sqlite3
from pathlib import Path

from app.problem_action_models import ProblemCorrectiveAction


class SQLiteProblemActionRepository:
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
                "CREATE TABLE IF NOT EXISTS problem_actions (action_id TEXT PRIMARY KEY, problem_id TEXT NOT NULL, payload_json TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_problem_actions_problem ON problem_actions(problem_id)"
            )

    def save(self, action: ProblemCorrectiveAction) -> ProblemCorrectiveAction:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO problem_actions(action_id, problem_id, payload_json) VALUES (?, ?, ?) "
                "ON CONFLICT(action_id) DO UPDATE SET problem_id=excluded.problem_id, payload_json=excluded.payload_json",
                (action.action_id, action.problem_id, action.model_dump_json()),
            )
        return action

    def get(self, action_id: str) -> ProblemCorrectiveAction | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM problem_actions WHERE action_id = ?", (action_id,)
            ).fetchone()
        return None if row is None else ProblemCorrectiveAction.model_validate_json(row["payload_json"])

    def list_for_problem(self, problem_id: str, *, limit: int = 500) -> list[ProblemCorrectiveAction]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM problem_actions WHERE problem_id = ? ORDER BY rowid LIMIT ?",
                (problem_id, limit),
            ).fetchall()
        return [ProblemCorrectiveAction.model_validate_json(row["payload_json"]) for row in rows]
