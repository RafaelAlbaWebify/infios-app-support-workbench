from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from app.analyzer import analyze_incident
from app.models import IncidentInput
from app.report_markdown import render_markdown_report
from app.run_history import save_run_history
from app.server import run_workbench_server


def _load_incident(path: Path) -> IncidentInput:
    data = json.loads(path.read_text(encoding="utf-8"))
    return IncidentInput.model_validate(data)


def _write_or_print(content: str, output_path: Path | None) -> None:
    if output_path is None:
        print(content)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infios",
        description="INFIOS local Application Support incident workbench.",
    )

    subcommands = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subcommands.add_parser(
        "analyze",
        help="Analyze an incident JSON file and write a support-ready report.",
    )
    analyze_parser.add_argument(
        "incident_json",
        type=Path,
        help="Path to an incident JSON file.",
    )
    analyze_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output file. If omitted, the result is printed to stdout.",
    )
    analyze_parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format. Default: markdown.",
    )
    analyze_parser.add_argument(
        "--save-history",
        action="store_true",
        help="Save a local run-history JSON record.",
    )
    analyze_parser.add_argument(
        "--history-dir",
        type=Path,
        default=None,
        help="Optional run-history directory. Default: runs/history.",
    )

    serve_parser = subcommands.add_parser(
        "serve",
        help="Start the local INFIOS web workbench.",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Listen address. Default: 127.0.0.1 (local machine only).",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        choices=range(1, 65536),
        metavar="PORT",
        help="TCP port from 1 to 65535. Default: 8000.",
    )
    serve_parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Optional SQLite database path. Default: runs/infios-cases.sqlite3.",
    )
    serve_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the workbench automatically in the default browser.",
    )

    return parser


def run_analyze(args: argparse.Namespace) -> int:
    incident_path: Path = args.incident_json

    if not incident_path.exists():
        print(f"ERROR: incident file not found: {incident_path}", file=sys.stderr)
        return 2

    if not incident_path.is_file():
        print(f"ERROR: incident path is not a file: {incident_path}", file=sys.stderr)
        return 2

    try:
        incident = _load_incident(incident_path)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {incident_path}: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(f"ERROR: incident schema validation failed for {incident_path}: {exc}", file=sys.stderr)
        return 2

    analysis = analyze_incident(incident)

    if args.format == "json":
        content = analysis.model_dump_json(indent=2)
    else:
        content = render_markdown_report(incident, analysis)

    _write_or_print(content, args.out)

    if args.save_history:
        history_path = save_run_history(
            incident,
            analysis,
            source_path=incident_path,
            output_path=args.out,
            output_format=args.format,
            history_dir=args.history_dir,
        )
        print(f"History saved: {history_path}", file=sys.stderr)

    return 0


def run_serve(args: argparse.Namespace) -> int:
    run_workbench_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        database_path=args.database,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return run_analyze(args)
    if args.command == "serve":
        return run_serve(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
