from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from app.cli import build_parser, main
from app.server import run_workbench_server


def test_serve_parser_uses_local_safe_defaults() -> None:
    args = build_parser().parse_args(["serve"])

    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.database is None
    assert args.no_browser is False


def test_cli_serve_passes_explicit_launch_options(tmp_path: Path) -> None:
    database_path = tmp_path / "cases.sqlite3"

    with patch("app.cli.run_workbench_server") as run_server:
        result = main(
            [
                "serve",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
                "--database",
                str(database_path),
                "--no-browser",
            ]
        )

    assert result == 0
    run_server.assert_called_once_with(
        host="127.0.0.1",
        port=8765,
        open_browser=False,
        database_path=database_path,
    )


def test_server_configures_database_and_uvicorn_without_real_launch(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "cases.sqlite3"

    with (
        patch("app.server.uvicorn.run") as uvicorn_run,
        patch("app.server.threading.Timer") as timer,
        patch.dict("os.environ", {}, clear=False),
    ):
        run_workbench_server(
            host="127.0.0.1",
            port=9000,
            open_browser=True,
            database_path=database_path,
        )

        timer.assert_called_once()
        timer.return_value.start.assert_called_once_with()
        uvicorn_run.assert_called_once_with(
            "app.main:app",
            host="127.0.0.1",
            port=9000,
            log_level="info",
        )

    assert database_path.parent.exists()


def test_server_does_not_schedule_browser_when_disabled() -> None:
    with (
        patch("app.server.uvicorn.run"),
        patch("app.server.threading.Timer") as timer,
    ):
        run_workbench_server(open_browser=False)

    timer.assert_not_called()
