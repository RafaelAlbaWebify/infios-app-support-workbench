import json
from datetime import datetime, timezone
from pathlib import Path

from app.analyzer import analyze_incident
from app.main import load_sample
from app.run_history import build_run_history_record, list_run_history, save_run_history


def test_build_run_history_record_contains_safe_support_boundary() -> None:
    incident = load_sample("incident-503-dependency.json")
    analysis = analyze_incident(incident)

    record = build_run_history_record(
        incident,
        analysis,
        source_path="samples/incident-503-dependency.json",
        output_path="reports/generated/demo.md",
        output_format="markdown",
        created_at=datetime(2026, 7, 8, 1, 0, tzinfo=timezone.utc),
    )

    assert record["run_id"] == "20260708T010000Z-infios-sample-503-dependency"
    assert record["incident_id"] == "INFIOS-SAMPLE-503-DEPENDENCY"
    assert "Dependency" in record["finding_categories"]
    assert record["severity_counts"]["high"] >= 1
    assert "No production connection" in record["support_boundary"]


def test_save_and_list_run_history(tmp_path: Path) -> None:
    incident = load_sample("incident-403-after-login.json")
    analysis = analyze_incident(incident)

    history_path = save_run_history(
        incident,
        analysis,
        source_path="samples/incident-403-after-login.json",
        output_path="reports/generated/403.md",
        output_format="markdown",
        history_dir=tmp_path,
    )

    assert history_path.exists()

    saved = json.loads(history_path.read_text(encoding="utf-8"))
    assert saved["incident_id"] == "INFIOS-SAMPLE-403-AFTER-LOGIN"
    assert "Authorization" in saved["finding_categories"]

    records = list_run_history(tmp_path)
    assert len(records) == 1
    assert records[0]["incident_id"] == "INFIOS-SAMPLE-403-AFTER-LOGIN"


def test_list_run_history_returns_empty_for_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert list_run_history(missing) == []
