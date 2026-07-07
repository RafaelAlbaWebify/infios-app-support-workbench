import json
from pathlib import Path

from app.cli import main


def test_cli_writes_markdown_report(tmp_path: Path) -> None:
    output_path = tmp_path / "cli-503-report.md"

    exit_code = main(
        [
            "analyze",
            "samples/incident-503-dependency.json",
            "--out",
            str(output_path),
        ]
    )

    assert exit_code == 0
    report = output_path.read_text(encoding="utf-8")
    assert "# INFIOS Incident Report - INFIOS-SAMPLE-503-DEPENDENCY" in report
    assert "Dependency" in report
    assert "Support Boundary" in report


def test_cli_prints_json_to_stdout(capsys) -> None:
    exit_code = main(
        [
            "analyze",
            "samples/incident-403-after-login.json",
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "INFIOS-SAMPLE-403-AFTER-LOGIN" in captured.out
    assert "Authorization" in captured.out
    assert captured.err == ""


def test_cli_missing_file_returns_error(capsys) -> None:
    exit_code = main(["analyze", "samples/does-not-exist.json"])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "incident file not found" in captured.err


def test_cli_saves_run_history_record(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "cli-503-report.md"
    history_dir = tmp_path / "history"

    exit_code = main(
        [
            "analyze",
            "samples/incident-503-dependency.json",
            "--out",
            str(output_path),
            "--save-history",
            "--history-dir",
            str(history_dir),
        ]
    )

    captured = capsys.readouterr()
    history_files = list(history_dir.glob("*.json"))

    assert exit_code == 0
    assert output_path.exists()
    assert "History saved:" in captured.err
    assert len(history_files) == 1

    record = json.loads(history_files[0].read_text(encoding="utf-8"))
    assert record["incident_id"] == "INFIOS-SAMPLE-503-DEPENDENCY"
    assert record["output_path"] == str(output_path)
    assert "Dependency" in record["finding_categories"]
    assert "No production connection" in record["support_boundary"]
