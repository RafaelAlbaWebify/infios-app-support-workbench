from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.handovers import get_handover_repository
from app.api.problem_actions import get_problem_action_repository
from app.api.problems import get_problem_repository
from app.application_attention import ApplicationOperationalAttentionReport, build_application_operational_attention_report
from app.persistence.sqlite_case_repository import SQLiteCaseRepository
from app.persistence.sqlite_evidence_repository import SQLiteEvidenceRepository
from app.persistence.sqlite_handover_repository import SQLiteHandoverRepository
from app.persistence.sqlite_problem_action_repository import SQLiteProblemActionRepository
from app.persistence.sqlite_problem_repository import SQLiteProblemRepository

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/application-attention", response_model=ApplicationOperationalAttentionReport)
def get_application_attention_report(
    case_repository: SQLiteCaseRepository = Depends(get_case_repository),
    problem_repository: SQLiteProblemRepository = Depends(get_problem_repository),
    action_repository: SQLiteProblemActionRepository = Depends(get_problem_action_repository),
    handover_repository: SQLiteHandoverRepository = Depends(get_handover_repository),
    evidence_repository: SQLiteEvidenceRepository = Depends(get_evidence_repository),
) -> ApplicationOperationalAttentionReport:
    cases, _ = case_repository.search(limit=5000, case_kind="real", archive_state="all")
    problems = problem_repository.list(active_only=False)
    actions_by_problem = {
        problem.problem_id: action_repository.list_for_problem(problem.problem_id, limit=500)
        for problem in problems
    }
    evidence_by_case = {
        case.case_id: evidence_repository.list_for_case(case.case_id, limit=500)
        for case in cases
    }
    handovers = handover_repository.list_recent(limit=200)
    return build_application_operational_attention_report(
        cases,
        problems,
        actions_by_problem,
        handovers,
        evidence_by_case,
    )
