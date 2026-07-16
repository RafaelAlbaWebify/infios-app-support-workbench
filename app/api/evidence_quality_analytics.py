from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.evidence_quality_analytics import (
    EvidenceQualityPortfolioReport,
    build_evidence_quality_portfolio_report,
)
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/evidence-quality", response_model=EvidenceQualityPortfolioReport)
def evidence_quality(
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
) -> EvidenceQualityPortfolioReport:
    cases, _ = case_repository.search(limit=500, archive_state="all", case_kind="real")
    evidence_by_case = {
        case.case_id: evidence_repository.list_for_case(case.case_id, limit=500) for case in cases
    }
    return build_evidence_quality_portfolio_report(cases, evidence_by_case)
