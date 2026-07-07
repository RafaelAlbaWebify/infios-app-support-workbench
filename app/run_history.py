from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import AnalysisResult, IncidentInput

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_HISTORY_DIR = ROOT_DIR / "runs" / "history"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip("-._")
    return cleaned.lower() or "incident"


def _severity_counts(analysis: AnalysisResult) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in analysis.findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def build_run_history_record(
    incident: IncidentInput,
    analysis: AnalysisResult,
    *,
    source_path: str | None = None,
    output_path: str | None = None,
    output_format: str = "markdown",
    created_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = created_at or datetime.now(timezone.utc)
    created_at_value = timestamp.isoformat().replace("+00:00", "Z")
    run_id = f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{_slug(incident.incident_id)}"

    return {
        "run_id": run_id,
        "created_at": created_at_value,
        "incident_id": incident.incident_id,
        "title": incident.title,
        "affected_service": incident.affected_service,
        "environment": incident.environment,
        "http_status": incident.http_status,
        "endpoint": incident.endpoint,
        "correlation_id": incident.correlation_id,
        "source_path": source_path,
        "output_path": output_path,
        "output_format": output_format,
        "finding_categories": [finding.category for finding in analysis.findings],
        "severity_counts": _severity_counts(analysis),
        "likely_cause_count": len(analysis.likely_causes),
        "unknown_count": len(analysis.unknowns),
        "missing_evidence_count": len(analysis.missing_evidence),
        "safe_next_step_count": len(analysis.safe_next_steps),
        "support_boundary": "Local sample-safe history record. No production connection, credential collection, database modification, or auto-remediation was performed.",
    }


def save_run_history(
    incident: IncidentInput,
    analysis: AnalysisResult,
    *,
    source_path: str | Path | None = None,
    output_path: str | Path | None = None,
    output_format: str = "markdown",
    history_dir: str | Path | None = None,
) -> Path:
    target_dir = Path(history_dir) if history_dir is not None else DEFAULT_HISTORY_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    record = build_run_history_record(
        incident,
        analysis,
        source_path=str(source_path) if source_path is not None else None,
        output_path=str(output_path) if output_path is not None else None,
        output_format=output_format,
    )

    target_path = target_dir / f"{record['run_id']}.json"
    target_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target_path


def list_run_history(history_dir: str | Path | None = None, limit: int = 20) -> list[dict[str, Any]]:
    target_dir = Path(history_dir) if history_dir is not None else DEFAULT_HISTORY_DIR
    if not target_dir.exists():
        return []

    records: list[dict[str, Any]] = []
    for path in sorted(target_dir.glob("*.json"), reverse=True):
        records.append(json.loads(path.read_text(encoding="utf-8")))
        if len(records) >= limit:
            break

    return records
