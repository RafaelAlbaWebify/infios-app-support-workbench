from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from pydantic import BaseModel

from app.domain.models import EvidenceItem, SupportCase
from app.evidence_validation import build_evidence_validation_report


DISCLAIMER = (
    "Evidence-quality signals describe stored metadata and automated review flags only. "
    "They are not a case-quality score, do not assess operator performance, and do not prove or disprove an explanation."
)


class EvidenceCaseAttention(BaseModel):
    case_id: str
    application: str
    evidence_count: int
    attention_required_count: int
    issue_counts: dict[str, int]


class EvidenceQualityPortfolioReport(BaseModel):
    generated_at: datetime
    total_cases: int
    cases_with_evidence: int
    cases_without_evidence: int
    total_evidence_items: int
    evidence_items_requiring_attention: int
    cases_requiring_attention: int
    certainty_counts: dict[str, int]
    sensitivity_counts: dict[str, int]
    evidence_type_counts: dict[str, int]
    issue_counts: dict[str, int]
    attention_cases: list[EvidenceCaseAttention]
    disclaimer: str = DISCLAIMER


def _ordered(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0].lower())))


def build_evidence_quality_portfolio_report(
    cases: list[SupportCase], evidence_by_case: dict[str, list[EvidenceItem]]
) -> EvidenceQualityPortfolioReport:
    certainty: Counter[str] = Counter()
    sensitivity: Counter[str] = Counter()
    evidence_types: Counter[str] = Counter()
    issues: Counter[str] = Counter()
    attention_cases: list[EvidenceCaseAttention] = []
    total_evidence = attention_items = cases_with_evidence = 0

    for case in cases:
        evidence = evidence_by_case.get(case.case_id, [])
        if evidence:
            cases_with_evidence += 1
        total_evidence += len(evidence)
        for item in evidence:
            certainty[item.certainty.value] += 1
            sensitivity[item.sensitivity.value] += 1
            evidence_types[item.evidence_type] += 1
        report = build_evidence_validation_report(evidence)
        attention_items += report.attention_required_count
        issues.update(report.issue_counts)
        if report.attention_required_count:
            attention_cases.append(
                EvidenceCaseAttention(
                    case_id=case.case_id,
                    application=case.application,
                    evidence_count=report.evidence_count,
                    attention_required_count=report.attention_required_count,
                    issue_counts=dict(sorted(report.issue_counts.items())),
                )
            )

    attention_cases.sort(
        key=lambda item: (-item.attention_required_count, item.application.lower(), item.case_id)
    )
    return EvidenceQualityPortfolioReport(
        generated_at=datetime.now(timezone.utc),
        total_cases=len(cases),
        cases_with_evidence=cases_with_evidence,
        cases_without_evidence=len(cases) - cases_with_evidence,
        total_evidence_items=total_evidence,
        evidence_items_requiring_attention=attention_items,
        cases_requiring_attention=len(attention_cases),
        certainty_counts=_ordered(certainty),
        sensitivity_counts=_ordered(sensitivity),
        evidence_type_counts=_ordered(evidence_types),
        issue_counts=_ordered(issues),
        attention_cases=attention_cases,
    )
