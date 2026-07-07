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
        description="INFIOS local Application Support incident analyzer.",
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
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return run_analyze(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
