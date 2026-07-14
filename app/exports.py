from __future__ import annotations

from typing import Any


def render_case_summary_markdown(summary: Any) -> str:
    support_case = summary.case
    lines = [
        f"# Case summary: {support_case.title}",
        "",
        f"- Case ID: `{support_case.case_id}`",
        f"- Application: {support_case.application}",
        f"- Environment: {support_case.environment}",
        f"- Status: {support_case.status.value}",
        f"- Severity: {support_case.severity}",
        f"- Impact: {support_case.impact}",
        f"- Affected scope: {support_case.affected_scope}",
        "",
        "## Evidence",
        "",
    ]
    lines.extend(
        [
            f"- [{item.certainty.value}] {item.evidence_type.value}: {item.content} — source: {item.source} (`{item.evidence_id}`)"
            for item in summary.evidence
        ]
        or ["- None recorded."]
    )
    lines.extend(["", "## Evidence-backed observations", ""])
    lines.extend(
        [f"- [{item.certainty.value}] {item.statement} (`{item.observation_id}`)" for item in summary.observations]
        or ["- None recorded."]
    )
    lines.extend(["", "## Diagnostic actions", ""])
    lines.extend(
        [
            f"- {item.name} [{item.status.value}]: {item.actual_result or 'No result recorded.'}"
            for item in summary.actions
        ]
        or ["- None recorded."]
    )
    lines.extend(["", "## Possible explanations", ""])
    lines.extend(
        [f"- [{item.status.value}] {item.statement}" for item in summary.explanations]
        or ["- None recorded."]
    )
    lines.extend(["", "## Recovery validation", ""])
    lines.extend(
        [f"- [{item.outcome.value}] {item.method}: {item.result}" for item in summary.recovery_validations]
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
