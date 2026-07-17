from concurrent.futures import ThreadPoolExecutor

from app.domain.models import CaseStatus, SupportCase
from app.persistence.sqlite_case_repository import SQLiteCaseRepository


def _case(index: int) -> SupportCase:
    return SupportCase(
        case_id=f"case-{index:04d}",
        title=f"Representative case {index}",
        application="Order Management" if index % 2 == 0 else "Warehouse Control",
        status=CaseStatus.INVESTIGATION if index % 3 else CaseStatus.WAITING_FOR_ESCALATION,
        owner="L2 Support" if index % 4 else None,
        severity="high" if index % 5 == 0 else "medium",
        is_demo=index % 7 == 0,
    )


def test_bulk_case_persistence_and_filtered_counts_are_consistent(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "cases.sqlite3")
    for index in range(240):
        repository.save(_case(index))

    visible, total = repository.search(limit=300, archive_state="all")
    assert total == 240
    assert len(visible) == 240
    assert len({item.case_id for item in visible}) == 240

    investigations, investigation_total = repository.search(
        limit=300,
        status=CaseStatus.INVESTIGATION,
        archive_state="all",
    )
    assert investigation_total == 160
    assert all(item.status is CaseStatus.INVESTIGATION for item in investigations)

    assigned, assigned_total = repository.search(
        limit=300,
        owner="__assigned__",
        archive_state="all",
    )
    assert assigned_total == 180
    assert all(item.owner for item in assigned)

    matches, match_total = repository.search(
        limit=300,
        query="warehouse",
        archive_state="all",
    )
    assert match_total == 120
    assert all(item.application == "Warehouse Control" for item in matches)


def test_concurrent_readers_return_complete_consistent_snapshots(tmp_path) -> None:
    database = tmp_path / "cases.sqlite3"
    writer = SQLiteCaseRepository(database)
    for index in range(120):
        writer.save(_case(index))

    def read_snapshot(_: int) -> tuple[int, tuple[str, ...]]:
        repository = SQLiteCaseRepository(database)
        records, total = repository.search(limit=200, archive_state="all")
        return total, tuple(item.case_id for item in records)

    with ThreadPoolExecutor(max_workers=8) as pool:
        snapshots = list(pool.map(read_snapshot, range(32)))

    assert all(total == 120 for total, _ in snapshots)
    baseline = snapshots[0][1]
    assert len(baseline) == 120
    assert len(set(baseline)) == 120
    assert all(case_ids == baseline for _, case_ids in snapshots)
