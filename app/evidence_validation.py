from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity
from app.secret_scanning import scan_evidence_content


@dataclass(frozen=True)
class EvidenceValidationItem:
    evidence_id: str
    status: str
    issues: list[str]
    secret_finding_count: int


@dataclass(frozen=True)
class EvidenceValidationReport:
    status: str
    evidence_count: int
    attention_required_count: int
    issue_counts: dict[str, int]
    items: list[EvidenceValidationItem]


def build_evidence_validation_report(
    evidence_items: list[EvidenceItem],
) -> EvidenceValidationReport:
    items: list[EvidenceValidationItem] = []
    issue_counts: dict[str, int] = {}

    for evidence in evidence_items:
        secret_findings = scan_evidence_content(evidence.content)
        secret_finding_count = sum(finding.occurrences for finding in secret_findings)
        issues: list[str] = []

        if secret_finding_count:
            issues.append("possible_secret_material")
        if (
            evidence.sensitivity is EvidenceSensitivity.CREDENTIAL_OR_SECRET
            and not evidence.redacted
        ):
            issues.append("credential_evidence_not_redacted")
        if evidence.observed_at is None:
            issues.append("missing_observed_at")
        if evidence.certainty is CertaintyLevel.UNKNOWN:
            issues.append("unknown_certainty")

        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        items.append(
            EvidenceValidationItem(
                evidence_id=evidence.evidence_id,
                status="attention_required" if issues else "clean",
                issues=issues,
                secret_finding_count=secret_finding_count,
            )
        )

    attention_required_count = sum(
        1 for item in items if item.status == "attention_required"
    )
    return EvidenceValidationReport(
        status="attention_required" if attention_required_count else "clean",
        evidence_count=len(items),
        attention_required_count=attention_required_count,
        issue_counts=issue_counts,
        items=items,
    )
