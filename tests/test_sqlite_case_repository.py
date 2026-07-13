from datetime import datetime, timedelta, timezone

import pytest

from app.domain.models import CaseStatus, SupportCase
from app.persistence import SQLiteCaseRepository


def test_case_round_trip_preserves_domain_values(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "infios.db")
    support_case = SupportCase(
        case_id="case-001",
        title="Orders page fails after login",
        application="Order Management",
        environment="test",
        status=CaseStatus.INVESTIGATION,
        severity="high",
        impact="Order submission is blocked",
        owner="l1.operator",
        affected_scope="three users",
    )

    repository.save(support_case)

    restored = repository.get("case-001")
    assert restored == support_case
    assert restored is not None
    assert restored.status is CaseStatus.INVESTIGATION


def test_save_updates_existing_case_without_duplicate(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "infios.db")
    original = SupportCase(
        case_id="case-002",
        title="Feature error",
        application="Order Management",
    )
    repository.save(original)

    updated = original.model_copy(
        update={
            "status": CaseStatus.WAITING_FOR_ESCALATION,
            "owner": "l2.engineer",
            "updated_at": original.updated_at + timedelta(minutes=5),
        }
    )
    repository.save(updated)

    assert repository.get("case-002") == updated
    assert repository.list() == [updated]


def test_list_orders_cases_by_latest_update_and_applies_limit(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "infios.db")
    base_time = datetime(2026, 7, 14, 10, 0, tzinfo=timezone.utc)
    older = SupportCase(
        case_id="case-old",
        title="Older case",
        application="App A",
        updated_at=base_time,
    )
    newer = SupportCase(
        case_id="case-new",
        title="Newer case",
        application="App B",
        updated_at=base_time + timedelta(minutes=10),
    )

    repository.save(older)
    repository.save(newer)

    assert [item.case_id for item in repository.list(limit=1)] == ["case-new"]


def test_get_returns_none_for_unknown_case(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "infios.db")

    assert repository.get("missing") is None


def test_list_rejects_invalid_limit(tmp_path) -> None:
    repository = SQLiteCaseRepository(tmp_path / "infios.db")

    with pytest.raises(ValueError, match="limit must be at least 1"):
        repository.list(limit=0)
