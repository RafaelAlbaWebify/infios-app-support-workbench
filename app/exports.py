from __future__ import annotations

from typing import Any


def _value(item: Any) -> str:
    return str(getattr(item, "value", item))


def render_case_summary_markdown(summary: Any) -> str:
    support_case = summary.case
    lines = [
        f"# Case summary: {support_case.title}",
        "",
        f"- Case ID: `{support_case.case_id}`",
        f"- Application: {support_case.application}",
        f"- Environment: {support_case.environment}",
        f"- Status: {_value(support_case.status)}",
        f"- Severity: {support_case.severity}",
        f"- Impact: {support_case.impact}",
        f"- Affected scope: {support_case.affected_scope}",
        "",
        "## Evidence",
        "",
    ]
    lines.extend(
        [
            f"- [{_value(item.certainty)}] {_value(item.evidence_type)}: {item.content} — source: {item.source} (`{item.evidence_id}`)"
            for item in summary.evidence
        ]
        or ["- None recorded."]
    )
    lines.extend(["", "## Evidence-backed observations", ""])
    lines.extend(
        [f"- [{_value(item.certainty)}] {item.statement} (`{item.observation_id}`)" for item in summary.observations]
        or ["- None recorded."]
    )
    lines.extend(["", "## Diagnostic actions", ""])
    lines.extend(
        [
            f"- {item.name} [{_value(item.status)}]: {item.actual_result or 'No result recorded.'}"
            for item in summary.actions
        ]
        or ["- None recorded."]
    )
    lines.extend(["", "## Possible explanations", ""])
    lines.extend(
        [f"- [{_value(item.status)}] {item.statement}" for item in summary.explanations]
        or ["- None recorded."]
    )
    lines.extend(["", "## Recovery validation", ""])
    lines.extend(
        [f"- [{_value(item.outcome)}] {item.method}: {item.result}" for item in summary.recovery_validations]
        or ["- None recorded."]
    )
    lines.extend(["", "## Escalation readiness", ""])
    lines.extend(
        [f"- {'Complete' if item.complete else 'Missing'} — {item.name}: {item.detail}" for item in summary.escalation_readiness]
    )
    lines.extend(
        [
            "",
            "## Next recommended action",
            "",
            summary.next_recommended_action,
            "",
            "## Safety statement",
            "",
            "This export separates evidence, observations, actions, possible explanations, and recovery validation. Unknown information remains explicit and no unconfirmed explanation is presented as root cause.",
        ]
    )
    return "\n".join(lines)
