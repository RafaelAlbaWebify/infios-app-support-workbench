from datetime import date, datetime, timezone

from app.application_attention import build_application_operational_attention_report
from app.domain.models import CaseStatus, CertaintyLevel, EvidenceItem, EvidenceSensitivity, SupportCase
from app.handover_models import HandoverCaseItem, ShiftHandover
from app.problem_action_models import ProblemActionSafety, ProblemActionStatus, ProblemActionType, ProblemCorrectiveAction
from app.problem_models import ProblemRecord, ProblemStatus

NOW = datetime(2026, 7, 16, tzinfo=timezone.utc)

def test_application_attention_keeps_signals_separate():
    case = SupportCase(case_id="case-1", title="Login failures", application="Portal", status=CaseStatus.BLOCKED, severity="high", owner=None, created_at=NOW, updated_at=NOW)
    evidence = EvidenceItem(evidence_id="ev-1", case_id="case-1", evidence_type="log", source="sample", content="bounded diagnostic sample", certainty=CertaintyLevel.UNKNOWN, sensitivity=EvidenceSensitivity.INTERNAL, collected_at=NOW)
    problem = ProblemRecord(problem_id="problem-1", title="Repeated login failures", summary="Repeated reports", status=ProblemStatus.INVESTIGATING, owner="team", created_by="analyst", case_ids=["case-1", "case-missing"], created_at=NOW, updated_at=NOW)
    action = ProblemCorrectiveAction(action_id="action-1", problem_id="problem-1", title="Review fix", description="Validate implementation", action_type=ProblemActionType.CORRECTIVE, status=ProblemActionStatus.BLOCKED, safety=ProblemActionSafety.ESCALATION_REQUIRED, owner="team", created_by="analyst", due_date=date(2026, 7, 10), created_at=NOW, updated_at=NOW)
    handover = ShiftHandover(handover_id="handover-1", shift_label="night", prepared_by="analyst", summary="Needs attention", cases=[HandoverCaseItem(case_id="case-1", status_summary="Blocked", next_action="Escalate", blocker="Vendor response", attention_required=True)], created_at=NOW)

    report = build_application_operational_attention_report([case], [problem], {"problem-1": [action]}, [handover], {"case-1": [evidence]}, today=date(2026, 7, 16))

    item = report.applications[0]
    assert report.application_count == 1
    assert item.application == "Portal"
    assert item.active_case_count == 1
    assert item.high_severity_active_case_count == 1
    assert item.unassigned_active_case_count == 1
    assert item.blocked_or_waiting_case_count == 1
    assert item.active_problem_count == 1
    assert item.recurring_problem_count == 1
    assert item.overdue_action_count == 1
    assert item.blocked_action_count == 1
    assert item.recent_handover_attention_count == 1
    assert item.recent_handover_blocker_count == 1
    assert item.evidence_attention_case_count == 1
    assert "not a combined risk score" in report.disclaimer

def test_demo_cases_are_excluded():
    demo = SupportCase(case_id="demo", title="Demo", application="Demo App", is_demo=True)
    report = build_application_operational_attention_report([demo], [], {}, [], {})
    assert report.application_count == 0
    assert report.applications == []
