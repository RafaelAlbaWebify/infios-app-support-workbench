from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.actions import get_action_repository
from app.api.cases import get_case_repository
from app.api.evidence import get_evidence_repository
from app.api.explanations import get_explanation_repository
from app.api.escalations import get_escalation_repository
from app.api.recovery import get_recovery_repository
from app.api.observations import get_observation_repository
from app.domain.models import (
    ActionSafetyLevel,
    ActionStatus,
    CaseStatus,
    CertaintyLevel,
    DiagnosticAction,
    EvidenceItem,
    EvidenceSensitivity,
    ExplanationStatus,
    EscalationPackage,
    Observation,
    PossibleExplanation,
    SupportCase,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])


class DemoSeedResponse(BaseModel):
    primary_case_id: str
    case_ids: list[str]
    created_or_refreshed: int


@router.post("/seed", response_model=DemoSeedResponse)
def seed_portfolio_demo(
    cases=Depends(get_case_repository),
    evidence=Depends(get_evidence_repository),
    observations=Depends(get_observation_repository),
    actions=Depends(get_action_repository),
    explanations=Depends(get_explanation_repository),
    escalations=Depends(get_escalation_repository),
    recoveries=Depends(get_recovery_repository),
) -> DemoSeedResponse:
    """Create a deterministic, sanitized portfolio dataset.

    Re-running the endpoint refreshes the same records rather than creating
    duplicate demo incidents.
    """
    now = datetime.now(timezone.utc)

    sql_case = SupportCase(
        case_id="case-demo-sql-timeout",
        title="Daily order report returns HTTP 500 after SQL timeout",
        application="Order Reporting Portal",
        environment="Production-like demo",
        status=CaseStatus.INVESTIGATION,
        severity="P2",
        impact="Daily operational reporting unavailable for business users",
        owner="Application Support L2",
        affected_scope="Multiple reporting users",
        is_demo=True,
        created_at=now,
        updated_at=now,
    )
    log_case = SupportCase(
        case_id="case-demo-checkout-correlation",
        title="Intermittent checkout failure after deployment",
        application="Checkout Service",
        environment="Production-like demo",
        status=CaseStatus.WAITING_FOR_ESCALATION,
        severity="P2",
        impact="Intermittent customer checkout failures",
        owner="Application Support L2",
        affected_scope="Subset of checkout requests",
        is_demo=True,
        created_at=now,
        updated_at=now,
    )
    cases.save(sql_case)
    cases.save(log_case)

    sql_http = evidence.save(EvidenceItem(
        evidence_id="evidence-demo-sql-http",
        case_id=sql_case.case_id,
        evidence_type="http_observation",
        source="Sanitized browser/API capture",
        content="POST /reports/orders/daily returned HTTP 500 at 09:05 UTC. correlationId=demo-sql-0905.",
        certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
        redacted=True,
    ))
    sql_log = evidence.save(EvidenceItem(
        evidence_id="evidence-demo-sql-log",
        case_id=sql_case.case_id,
        evidence_type="log_sample",
        source="Sanitized application log",
        content="correlationId=demo-sql-0905 report=DailyOrders procedure=sample_sp_daily_order_report error=Execution Timeout Expired duration=30s",
        certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
        redacted=True,
    ))
    sql_compare = evidence.save(EvidenceItem(
        evidence_id="evidence-demo-sql-compare",
        case_id=sql_case.case_id,
        evidence_type="reproduction_result",
        source="Approved sample-data reproduction",
        content="7-day range completed successfully; 90-day range reproduced the timeout. No database writes or configuration changes performed.",
        certainty=CertaintyLevel.REPRODUCED,
        sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
        redacted=True,
    ))
    obs_timeout = observations.save(Observation(
        observation_id="observation-demo-sql-timeout",
        case_id=sql_case.case_id,
        statement="The HTTP 500 and SQL timeout share correlation ID demo-sql-0905.",
        category="http_api",
        evidence_ids=[sql_http.evidence_id, sql_log.evidence_id],
        certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
    ))
    obs_range = observations.save(Observation(
        observation_id="observation-demo-sql-range",
        case_id=sql_case.case_id,
        statement="A 7-day sample succeeds while a 90-day sample reproduces the timeout.",
        category="performance",
        evidence_ids=[sql_compare.evidence_id],
        certainty=CertaintyLevel.REPRODUCED,
    ))
    action = actions.save(DiagnosticAction(
        action_id="action-demo-sql-compare",
        case_id=sql_case.case_id,
        name="Compare safe report ranges",
        purpose="Determine whether failure correlates with the requested data range without changing production data.",
        safety_level=ActionSafetyLevel.L1_SAFE,
        status=ActionStatus.COMPLETED,
        expected_result="Record whether small and large sample ranges behave differently.",
        actual_result="7-day range succeeded; 90-day range reproduced the 30-second timeout.",
        conclusion="Failure is reproducible for the larger range; database root cause remains unconfirmed.",
        evidence_ids=[sql_compare.evidence_id],
        performed_by="Application Support L2",
        started_at=now,
        completed_at=now,
    ))
    explanations.save(PossibleExplanation(
        explanation_id="explanation-demo-sql-volume",
        case_id=sql_case.case_id,
        statement="The reporting path may have a data-volume or execution-plan regression affecting larger ranges.",
        status=ExplanationStatus.SUPPORTED,
        supporting_observation_ids=[obs_timeout.observation_id, obs_range.observation_id],
        validation_action_ids=[action.action_id],
    ))

    log_http = evidence.save(EvidenceItem(
        evidence_id="evidence-demo-log-http",
        case_id=log_case.case_id,
        evidence_type="http_observation",
        source="Sanitized request trace",
        content="POST /checkout/submit intermittently returned HTTP 500; correlationId=demo-checkout-441.",
        certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
        redacted=True,
    ))
    log_pattern = evidence.save(EvidenceItem(
        evidence_id="evidence-demo-log-pattern",
        case_id=log_case.case_id,
        evidence_type="log_sample",
        source="Sanitized application logs",
        content="18 occurrences of SamplePaymentMappingException on instance app-02 after deployment; correlationId=demo-checkout-441.",
        certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
        redacted=True,
    ))
    log_obs = observations.save(Observation(
        observation_id="observation-demo-log-pattern",
        case_id=log_case.case_id,
        statement="The repeated exception is concentrated on app-02 and appears in the same request correlation chain as the HTTP 500.",
        category="application_behavior",
        evidence_ids=[log_http.evidence_id, log_pattern.evidence_id],
        certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
    ))
    explanations.save(PossibleExplanation(
        explanation_id="explanation-demo-log-deployment",
        case_id=log_case.case_id,
        statement="A deployment-specific application path may be contributing to the repeated mapping exception on app-02.",
        status=ExplanationStatus.SUPPORTED,
        supporting_observation_ids=[log_obs.observation_id],
    ))

    escalation_report = """# Escalation: Daily order report returns HTTP 500 after SQL timeout

## Confirmed observations
- HTTP 500 and SQL timeout share correlation ID demo-sql-0905.
- 7-day range succeeds while 90-day range reproduces the timeout.

## Diagnostic result
- Safe range comparison reproduced the 30-second timeout without database writes or configuration changes.

## Possible explanation — unconfirmed
- A data-volume or execution-plan regression may affect larger report ranges.

## Requested support
- DBA/Application Engineering: review the sanitized execution context and query-plan evidence for the large-range request. Do not perform production changes from this demo.

## Safety statement
Correlation and timing narrow the investigation; they do not prove root cause.
"""
    escalations.save(EscalationPackage(
        package_id="escalation-demo-sql-dba",
        case_id=sql_case.case_id,
        target_team="DBA / Application Engineering",
        included_evidence_ids=[sql_http.evidence_id, sql_log.evidence_id, sql_compare.evidence_id],
        requested_action="Review execution context and query-plan evidence for the reproducible large-range timeout.",
        report_text=escalation_report,
        generated_at=now,
    ))

    recovery_evidence = evidence.save(EvidenceItem(
        evidence_id="evidence-demo-sql-recovery",
        case_id=sql_case.case_id,
        evidence_type="recovery_validation",
        source="Sanitized post-change validation",
        content="After the simulated downstream remediation, the 90-day sample completed successfully twice and returned the expected record count.",
        certainty=CertaintyLevel.REPRODUCED,
        sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
        redacted=True,
    ))
    recoveries.save(RecoveryValidation(
        validation_id="recovery-demo-sql-passed",
        case_id=sql_case.case_id,
        outcome=RecoveryOutcome.PASSED,
        method="Repeat the previously failing 90-day report twice and compare expected record count.",
        result="Both validation runs completed successfully with the expected sample result.",
        performed_by="Application Support L2",
        evidence_ids=[recovery_evidence.evidence_id],
        notes="Recovery evidence demonstrates restored behavior; it does not independently prove the underlying root cause.",
        tested_at=now,
    ))

    return DemoSeedResponse(
        primary_case_id=sql_case.case_id,
        case_ids=[sql_case.case_id, log_case.case_id],
        created_or_refreshed=2,
    )
