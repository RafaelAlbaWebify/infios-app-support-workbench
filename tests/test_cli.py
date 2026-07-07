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
