from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.problems import get_problem_repository
from app.domain.models import CaseStatus, SupportCase
from app.main import app
from app.operational_analytics import build_operational_snapshot
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository
from app.problem_models import ProblemRecord, ProblemStatus


def test_operational_snapshot_counts_metadata() -> None:
    archived = SupportCase(
        title="Old API failure",
        application="Orders API",
        status=CaseStatus.CLOSED,
        severity="high",
        owner="Team A",
        archived_at=datetime.now(timezone.utc),
        archived_by="operator-1",
        archive_reason="Historical record",
    )
    active = SupportCase(
        title="Current API failure",
        application="Orders API",
        status=CaseStatus.INVESTIGATION,
        severity="high",
        owner=None,
        is_demo=True,
    )
    problem = ProblemRecord(
        title="Recurring API failures",
        summary="Cases grouped by an operator.",
        owner="Problem Management",
        created_by="operator-1",
        case_ids=[archived.case_id, active.case_id],
        status=ProblemStatus.INVESTIGATING,
    )

    report = build_operational_snapshot([archived, active], [problem])

    assert report.case_total == 2
    assert report.active_case_total == 1
    assert report.archived_case_total == 1
    assert report.demo_case_total == 1
    assert report.real_case_total == 1
    assert report.unassigned_case_total == 1
    assert report.application_counts == {"Orders API": 2}
    assert report.problem_total == 1
    assert report.active_problem_total == 1
    assert report.recurring_problem_total == 1
    assert "do not establish causation" in report.disclaimer


def test_operational_snapshot_api(tmp_path) -> None:
    database = tmp_path / "workbench.sqlite3"
    case_repository = SQLiteCaseRepository(database)
    problem_repository = SQLiteProblemRepository(database)
    first = case_repository.save(
        SupportCase(
            title="Login issue",
            application="Portal",
            status=CaseStatus.INVESTIGATION,
            severity="medium",
            owner="Support",
        )
    )
    second = case_repository.save(
        SupportCase(
            title="Archived login issue",
            application="Portal",
            status=CaseStatus.CLOSED,
            severity="medium",
            archived_at=datetime.now(timezone.utc),
            archived_by="operator-1",
            archive_reason="Closed history",
        )
    )
    problem_repository.save(
        ProblemRecord(
            title="Portal login recurrence",
            summary="Explicitly grouped incidents.",
            owner="Support",
            created_by="operator-1",
            case_ids=[first.case_id, second.case_id],
        )
    )

    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_problem_repository] = lambda: problem_repository
    client = TestClient(app)
    try:
        response = client.get("/api/analytics/operational-snapshot")
        assert response.status_code == 200
        payload = response.json()
        assert payload["case_total"] == 2
        assert payload["archived_case_total"] == 1
        assert payload["application_counts"] == {"Portal": 2}
        assert payload["problem_total"] == 1
        assert payload["recurring_problem_total"] == 1
    finally:
        app.dependency_overrides.clear()
