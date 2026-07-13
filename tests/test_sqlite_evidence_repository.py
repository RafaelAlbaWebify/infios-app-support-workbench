from datetime import datetime, timezone

from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


def _evidence(case_id: str, detail: str, minute: int) -> EvidenceItem:
    return EvidenceItem(
        case_id=case_id,
        evidence_type="user_report",
        source="service desk",
        observed_at=datetime(2026, 7, 14, 10, minute, tzinfo=timezone.utc),
        collected_at=datetime(2026, 7, 14, 10, minute + 1, tzinfo=timezone.utc),
        content=detail,
        certainty=CertaintyLevel.REPORTED,
        sensitivity=EvidenceSensitivity.INTERNAL,
    )


def test_evidence_round_trip_and_case_isolation(tmp_path) -> None:
    repository = SQLiteEvidenceRepository(tmp_path / "cases.sqlite3")
    first = _evidence("case-1", "Orders page fails", 1)
    second = _evidence("case-2", "Other case", 2)

    repository.save(first)
    repository.save(second)

    assert repository.get(first.evidence_id) == first
    assert repository.list_for_case("case-1") == [first]
    assert repository.list_for_case("case-2") == [second]


def test_evidence_listing_is_chronological_and_bounded(tmp_path) -> None:
    repository = SQLiteEvidenceRepository(tmp_path / "cases.sqlite3")
    later = _evidence("case-1", "Later", 5)
    earlier = _evidence("case-1", "Earlier", 1)
    repository.save(later)
    repository.save(earlier)

    assert repository.list_for_case("case-1") == [earlier, later]
    assert repository.list_for_case("case-1", limit=1) == [earlier]


def test_unknown_evidence_returns_none_and_invalid_limit_fails(tmp_path) -> None:
    repository = SQLiteEvidenceRepository(tmp_path / "cases.sqlite3")

    assert repository.get("evidence-missing") is None

    try:
        repository.list_for_case("case-1", limit=0)
    except ValueError as exc:
        assert str(exc) == "limit must be at least 1"
    else:
        raise AssertionError("Expected ValueError for invalid limit")
