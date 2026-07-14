from app.api.ui import UI_DIR


def test_navigation_loads_archive_module() -> None:
    navigation = (UI_DIR / "navigation.js").read_text(encoding="utf-8")
    assert "archive.js" in navigation


def test_archive_module_exposes_filters_creation_and_reversible_actions() -> None:
    script = (UI_DIR / "archive.js").read_text(encoding="utf-8")

    assert 'id="case-kind-filter"' in script
    assert 'id="case-archive-filter"' in script
    assert 'id="create-demo-case"' in script
    assert "payload.is_demo" in script
    assert "archive_state" in script
    assert "case_kind" in script
    assert "archive-action" in script
    assert "Restore incident" in script
    assert "Archive incident" in script
    assert "performed_by" in script
    assert "archive_history" in script
    assert "originalFetch(`/api/cases/${supportCase.case_id}/${action}`" in script


def test_archive_module_only_augments_case_list_and_create_requests() -> None:
    script = (UI_DIR / "archive.js").read_text(encoding="utf-8")

    assert "url.startsWith('/api/cases?')" in script
    assert "url === '/api/cases'" in script
    assert "return originalFetch(nextInput, nextInit);" in script
