from __future__ import annotations

from app.models import AnalysisResult, IncidentInput


def _bullet(items: list[str]) -> str:
    if not items:
        return "- None captured."
    return "\n".join(f"- {item}" for item in items)


def render_markdown_report(incident: IncidentInput, analysis: AnalysisResult) -> str:
    evidence_rows = [
        f"| {item.source} | {item.timestamp or 'Unknown'} | {item.confidence} | {item.detail} |"
        for item in incident.evidence
    ]
    evidence_table = "\n".join(evidence_rows) if evidence_rows else "| None | Unknown | low | No evidence items provided. |"

    finding_rows = [
        f"| {finding.category} | {finding.severity} | {finding.statement} | {', '.join(finding.evidence_refs) or 'n/a'} |"
        for finding in analysis.findings
    ]
    finding_table = "\n".join(finding_rows) if finding_rows else "| None | info | No findings generated. | n/a |"

    return f"""# INFIOS Incident Report - {incident.incident_id}

## Incident Summary

{analysis.summary}

## User Impact

{analysis.user_impact}

## Incident Metadata

| Field | Value |
|---|---|
| Title | {incident.title} |
| Service | {incident.affected_service} |
| Environment | {incident.environment} |
| HTTP Status | {incident.http_status or 'Unknown'} |
| Endpoint | {incident.endpoint or 'Unknown'} |
| Correlation ID | {incident.correlation_id or 'Not provided'} |

## Evidence Table

| Source | Timestamp | Confidence | Detail |
|---|---:|---|---|
{evidence_table}

## Findings

| Category | Severity | Statement | Evidence References |
|---|---|---|---|
{finding_table}

## Likely Causes - Not Confirmed

{_bullet(analysis.likely_causes)}

## Unknowns

{_bullet(analysis.unknowns)}

## Missing Evidence

{_bullet(analysis.missing_evidence)}

## Safe Next Steps

{_bullet(analysis.safe_next_steps)}

## Escalation Note

{analysis.escalation_note}

## RCA Draft

{analysis.rca_draft}

## Support Boundary

This report is evidence-first. It does not confirm root cause without logs, dependency evidence, or owner validation.
"""
