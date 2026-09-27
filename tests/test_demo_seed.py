from fastapi.testclient import TestClient

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.explanations import get_explanation_repository
from app.api.observations import get_observation_repository
from app.api.escalations import get_escalation_repository
from app.api.recovery import get_recovery_repository
from app.main import app
from app.persistence.sqlite_action_repository import SQLiteActionRepository
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_explanation_repository import SQLiteExplanationRepository
from app.persistence.sqlite_observation_repository import SQLiteObservationRepository
from app.persistence.sqlite_escalation_repository import SQLiteEscalationRepository
from app.persistence.sqlite_recovery_repository import SQLiteRecoveryRepository


def test_demo_seed_is_idempotent_and_builds_evidence_backed_n2_case(tmp_path) -> None:
    database = tmp_path / "demo.sqlite3"
    cases = SQLiteCaseRepository(database)
    evidence = SQLiteEvidenceRepository(database)
    observations = SQLiteObservationRepository(database)
    actions = SQLiteActionRepository(database)
    explanations = SQLiteExplanationRepository(database)
    escalations = SQLiteEscalationRepository(database)
    recoveries = SQLiteRecoveryRepository(database)

    app.dependency_overrides[get_case_repository] = lambda: cases
    app.dependency_overrides[get_evidence_repository] = lambda: evidence
    app.dependency_overrides[get_observation_repository] = lambda: observations
    app.dependency_overrides[get_action_repository] = lambda: actions
    app.dependency_overrides[get_explanation_repository] = lambda: explanations
    app.dependency_overrides[get_escalation_repository] = lambda: escalations
    app.dependency_overrides[get_recovery_repository] = lambda: recoveries
    client = TestClient(app)

    try:
        first = client.post("/api/demo/seed")
        second = client.post("/api/demo/seed")
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["primary_case_id"] == "case-demo-sql-timeout"

        stored_cases, count = cases.search(case_kind="demo", archive_state="active")
        assert count == 2
        assert len(stored_cases) == 2

        sql_case = cases.get("case-demo-sql-timeout")
        assert sql_case is not None
        assert sql_case.severity == "P2"
        assert sql_case.owner == "Application Support L2"
        assert sql_case.status.value == "investigation"

        sql_evidence = evidence.list_for_case(sql_case.case_id)
        sql_observations = observations.list_for_case(sql_case.case_id)
        sql_actions = actions.list_for_case(sql_case.case_id)
        sql_explanations = explanations.list_for_case(sql_case.case_id)

        assert len(sql_evidence) == 3
        assert len(sql_observations) == 2
        assert len(sql_actions) == 1
        assert sql_actions[0].actual_result
        assert len(sql_explanations) == 1
        assert sql_explanations[0].status.value == "supported"
        assert sql_explanations[0].confirmed_by_operator is False

        sql_escalations = escalations.list_for_case(sql_case.case_id)
        sql_recoveries = recoveries.list_for_case(sql_case.case_id)
        assert len(sql_escalations) == 1
        assert "do not prove root cause" in sql_escalations[0].report_text.lower()
        assert len(sql_recoveries) == 1
        assert sql_recoveries[0].outcome.value == "passed"
        assert sql_recoveries[0].evidence_ids == ["evidence-demo-sql-recovery"]
    finally:
        app.dependency_overrides.clear()
