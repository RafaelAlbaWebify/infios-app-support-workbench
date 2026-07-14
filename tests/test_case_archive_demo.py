import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.domain.models import CaseStatus, SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository, SCHEMA_VERSION


def test_repository_migrates_existing_case_table_without_hiding_cases(tmp_path) -> None:
    database = tmp_path / "legacy.sqlite3"
    case = SupportCase(
        case_id="case-legacy-001",
        title="Legacy case",
        application="Legacy App",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE support_cases (
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
            "INSERT INTO support_cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                case.case_id,
                case.title,
                case.application,
                case.status.value,
                case.severity,
                case.owner,
                case.updated_at.isoformat(),
                1,
                case.model_dump_json(),
            ),
        )

    repository = SQLiteCaseRepository(database)
    cases, count = repository.search()

    assert SCHEMA_VERSION == 2
    assert count == 1
    assert cases[0].case_id == case.case_id
    assert cases[0].is_demo is False
    assert cases[0].archived_at is None
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(support_cases)")}
    assert {"is_demo", "archived_at"}.issubset(columns)


def test_repository_filters_demo_and_archive_state(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    real = repository.save(SupportCase(title="Real", application="App"))
    demo = repository.save(SupportCase(title="Demo", application="App", is_demo=True))
    archived = repository.save(
        SupportCase(
            title="Archived",
            application="App",
            archived_at=datetime.now(timezone.utc),
            archived_by="L1",
            archive_reason="Training complete",
        )
    )

    active, count = repository.search()
    assert count == 2
    assert {item.case_id for item in active} == {real.case_id, demo.case_id}

    demos, count = repository.search(case_kind="demo")
    assert count == 1
    assert demos[0].case_id == demo.case_id

    archived_cases, count = repository.search(archive_state="archived")
    assert count == 1
    assert archived_cases[0].case_id == archived.case_id

    all_cases, count = repository.search(archive_state="all")
    assert count == 3
    assert len(all_cases) == 3


def test_api_archives_and_restores_with_attributed_history(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    app.dependency_overrides[get_case_repository] = lambda: repository
    client = TestClient(app)

    try:
        created = client.post(
            "/api/cases",
            json={
                "title": "Training incident",
                "application": "Sample App",
                "is_demo": True,
            },
        )
        assert created.status_code == 201
        case_id = created.json()["case_id"]
        assert created.json()["is_demo"] is True

        archived = client.post(
            f"/api/cases/{case_id}/archive",
            json={"performed_by": "Rafael", "reason": "Training completed"},
        )
        assert archived.status_code == 200
        archived_payload = archived.json()
        assert archived_payload["archived_at"] is not None
        assert archived_payload["archive_history"][-1]["action"] == "archived"

        default_list = client.get("/api/cases")
        assert default_list.status_code == 200
        assert default_list.json()["count"] == 0

        archived_list = client.get(
            "/api/cases", params={"archive_state": "archived", "case_kind": "demo"}
        )
        assert archived_list.status_code == 200
        assert archived_list.json()["count"] == 1

        blocked_edit = client.patch(
            f"/api/cases/{case_id}",
            json={"owner": "L2", "changed_by": "Rafael"},
        )
        assert blocked_edit.status_code == 409

        restored = client.post(
            f"/api/cases/{case_id}/restore",
            json={"performed_by": "Rafael", "reason": "Needed for another demo"},
        )
        assert restored.status_code == 200
        restored_payload = restored.json()
        assert restored_payload["archived_at"] is None
        assert [event["action"] for event in restored_payload["archive_history"]] == [
            "archived",
            "restored",
        ]

        duplicate_restore = client.post(
            f"/api/cases/{case_id}/restore",
            json={"performed_by": "Rafael", "reason": "Duplicate"},
        )
        assert duplicate_restore.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_dashboard_counts_ignore_archived_cases(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    repository.save(
        SupportCase(
            title="Active",
            application="App",
            status=CaseStatus.INVESTIGATION,
        )
    )
    repository.save(
        SupportCase(
            title="Archived active",
            application="App",
            status=CaseStatus.INVESTIGATION,
            archived_at=datetime.now(timezone.utc),
        )
    )

    counts = repository.dashboard_counts(
        resolved_since=datetime(2026, 7, 14, tzinfo=timezone.utc)
    )
    assert counts["open_cases"] == 1
