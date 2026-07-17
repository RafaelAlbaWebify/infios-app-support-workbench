from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.domain.models import SupportCase
from app.main import app
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


def test_repeated_log_imports_remain_complete_unique_and_read_consistent(tmp_path) -> None:
    database = tmp_path / "cases.sqlite3"
    case_repository = SQLiteCaseRepository(database)
    evidence_repository = SQLiteEvidenceRepository(database)
    support_case = case_repository.save(
        SupportCase(case_id="case-repeated-imports", title="Repeated imports", application="Orders")
    )
    app.dependency_overrides[get_case_repository] = lambda: case_repository
    app.dependency_overrides[get_evidence_repository] = lambda: evidence_repository
    client = TestClient(app)

    try:
        imported_ids: list[str] = []
        for index in range(60):
            response = client.post(
                f"/api/cases/{support_case.case_id}/evidence/import-log",
                json={
                    "source": f"Approved sample {index}",
                    "content": f"2026-07-17T12:{index:02d}:00Z request_id=req-{index:03d} status=503",
                    "certainty": "technically_confirmed",
                    "sensitivity": "internal",
                },
            )
            assert response.status_code == 201
            payload = response.json()
            assert payload["redactions"] == {}
            assert payload["line_count"] == 1
            assert payload["evidence"]["redacted"] is True
            imported_ids.append(payload["evidence"]["evidence_id"])

        assert len(imported_ids) == 60
        assert len(set(imported_ids)) == 60

        stored = evidence_repository.list_for_case(support_case.case_id, limit=100)
        assert [item.evidence_id for item in stored] == imported_ids
        assert all(item.evidence_type == "log_sample" for item in stored)
        assert all("request_id=req-" in str(item.content) for item in stored)

        def read_snapshot() -> list[str]:
            return [
                item.evidence_id
                for item in evidence_repository.list_for_case(support_case.case_id, limit=100)
            ]

        with ThreadPoolExecutor(max_workers=8) as executor:
            snapshots = list(executor.map(lambda _: read_snapshot(), range(24)))

        assert snapshots == [imported_ids] * 24
    finally:
        app.dependency_overrides.clear()
