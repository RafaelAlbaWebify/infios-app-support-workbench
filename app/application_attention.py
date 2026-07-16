from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from pydantic import BaseModel

from app.domain.models import CaseStatus, EvidenceItem, SupportCase
from app.evidence_validation import build_evidence_validation_report
from app.handover_models import ShiftHandover
from app.problem_action_models import ProblemActionStatus, ProblemCorrectiveAction
from app.problem_models import ProblemRecord, ProblemStatus

DISCLAIMER = (
    "Application attention signals are separate descriptive counts from explicitly stored records. "
    "They are not a combined risk score and do not prove service health, incident causation, ownership, or support performance."
)

class ApplicationAttentionItem(BaseModel):
    application: str
    active_case_count: int
    high_severity_active_case_count: int
    unassigned_active_case_count: int
    blocked_or_waiting_case_count: int
    active_problem_count: int
    recurring_problem_count: int
    overdue_action_count: int
    blocked_action_count: int
    validation_pending_action_count: int
    recent_handover_attention_count: int
    recent_handover_blocker_count: int
    evidence_attention_case_count: int
    cases_without_evidence_count: int

class ApplicationOperationalAttentionReport(BaseModel):
    generated_at: datetime
    application_count: int
    applications: list[ApplicationAttentionItem]
    disclaimer: str = DISCLAIMER

_ACTIVE_CASE_EXCLUSIONS = {CaseStatus.RESOLVED, CaseStatus.CLOSED}
_WAITING_STATUSES = {CaseStatus.WAITING_FOR_USER, CaseStatus.WAITING_FOR_ESCALATION, CaseStatus.WAITING_FOR_ANOTHER_TEAM, CaseStatus.BLOCKED}
_HIGH_SEVERITIES = {"critical", "high", "sev1", "sev2", "p1", "p2"}
_ACTIVE_PROBLEM_EXCLUSIONS = {ProblemStatus.RESOLVED, ProblemStatus.CLOSED}

def build_application_operational_attention_report(cases: list[SupportCase], problems: list[ProblemRecord], actions_by_problem: dict[str, list[ProblemCorrectiveAction]], handovers: list[ShiftHandover], evidence_by_case: dict[str, list[EvidenceItem]], *, today: date | None = None) -> ApplicationOperationalAttentionReport:
    today = today or datetime.now(timezone.utc).date()
    real_cases = [case for case in cases if not case.is_demo]
    case_by_id = {case.case_id: case for case in real_cases}
    applications = sorted({case.application for case in real_cases}, key=str.lower)
    signals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for case in real_cases:
        app = case.application
        is_active = case.archived_at is None and case.status not in _ACTIVE_CASE_EXCLUSIONS
        evidence = evidence_by_case.get(case.case_id, [])
        if is_active:
            signals[app]["active_case_count"] += 1
            if case.severity.strip().lower() in _HIGH_SEVERITIES: signals[app]["high_severity_active_case_count"] += 1
            if not case.owner or not case.owner.strip(): signals[app]["unassigned_active_case_count"] += 1
            if case.status in _WAITING_STATUSES: signals[app]["blocked_or_waiting_case_count"] += 1
        if not evidence: signals[app]["cases_without_evidence_count"] += 1
        elif build_evidence_validation_report(evidence).attention_required_count: signals[app]["evidence_attention_case_count"] += 1
    problem_apps: dict[str, set[str]] = {}
    for problem in problems:
        linked_apps = {case_by_id[cid].application for cid in problem.case_ids if cid in case_by_id}
        problem_apps[problem.problem_id] = linked_apps
        if problem.status not in _ACTIVE_PROBLEM_EXCLUSIONS:
            for app in linked_apps:
                signals[app]["active_problem_count"] += 1
                if problem.occurrence_count > 1: signals[app]["recurring_problem_count"] += 1
    for problem_id, actions in actions_by_problem.items():
        for action in actions:
            if action.status is ProblemActionStatus.CANCELLED: continue
            for app in problem_apps.get(problem_id, set()):
                if action.status is ProblemActionStatus.BLOCKED: signals[app]["blocked_action_count"] += 1
                if action.status is ProblemActionStatus.IMPLEMENTED: signals[app]["validation_pending_action_count"] += 1
                if action.due_date and action.due_date < today and action.status is not ProblemActionStatus.VALIDATED: signals[app]["overdue_action_count"] += 1
    for handover in handovers:
        for item in handover.cases:
            case = case_by_id.get(item.case_id)
            if case is None: continue
            if item.attention_required: signals[case.application]["recent_handover_attention_count"] += 1
            if item.blocker: signals[case.application]["recent_handover_blocker_count"] += 1
    items = [ApplicationAttentionItem(application=app, **signals[app]) for app in applications]
    items.sort(key=lambda item: (-item.high_severity_active_case_count, -item.blocked_or_waiting_case_count, -item.overdue_action_count, -item.evidence_attention_case_count, item.application.lower()))
    return ApplicationOperationalAttentionReport(generated_at=datetime.now(timezone.utc), application_count=len(items), applications=items)
