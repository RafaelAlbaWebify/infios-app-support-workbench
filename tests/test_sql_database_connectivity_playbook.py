from app.domain.models import CertaintyLevel, EvidenceItem, EvidenceSensitivity, Observation, SupportCase
from app.playbooks.sql_database_connectivity import evaluate_sql_database_connectivity


def test_sql_database_playbook_is_applicable_and_safety_focused() -> None:
    support_case = SupportCase(
        case_id="case-db",
        title="Order service reports SQL connection timeout",
        application="Order Management",
        affected_scope="multiple users",
        impact="order creation blocked",
    )
    evidence = [
        EvidenceItem(
            evidence_id="evidence-db",
            case_id=support_case.case_id,
            evidence_type="database_error",
            source="Sanitized application log",
            content="SQLSTATE HYT00 connection timeout at 10:15 UTC with correlation ID sample-db.",
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
        EvidenceItem(
            evidence_id="evidence-repro",
            case_id=support_case.case_id,
            evidence_type="reproduction_result",
            source="Approved bounded reproduction",
            content="The read-only order lookup timed out once in the affected environment.",
            certainty=CertaintyLevel.REPRODUCED,
            sensitivity=EvidenceSensitivity.PUBLIC_SAMPLE,
            redacted=True,
        ),
    ]
    observations = [
        Observation(
            observation_id="observation-db",
            case_id=support_case.case_id,
            statement="A bounded approved lookup reproduced the SQL timeout.",
            category="database",
            evidence_ids=["evidence-db", "evidence-repro"],
            certainty=CertaintyLevel.TECHNICALLY_CONFIRMED,
        )
    ]

    result = evaluate_sql_database_connectivity(support_case, evidence, observations)

    assert result.playbook_id == "sql-database-connectivity"
    assert result.applicable is True
    assert result.confirmed_observation_ids == ["observation-db"]
    assert len(result.recommended_checks) == 3
    assert all(check.safety_level.value == "l1_safe" for check in result.recommended_checks)
    assert any("Never collect" in warning for warning in result.safety_warnings)
    assert any("Do not run unbounded" in warning for warning in result.safety_warnings)


def test_sql_database_playbook_defers_generic_slowness_to_performance() -> None:
    support_case = SupportCase(case_id="case-slow", title="Application is slow", application="Order Management")

    result = evaluate_sql_database_connectivity(support_case, [], [])

    assert result.applicable is False
    assert "performance-degradation" in result.applicability_reasons[0]
    assert len(result.recommended_checks) == 1


def test_sql_database_playbook_does_not_treat_database_access_error_as_broad_connectivity() -> None:
    support_case = SupportCase(
        case_id="case-db-access",
        title="Database login failed for user due to invalid credentials",
        application="Order Management",
    )

    result = evaluate_sql_database_connectivity(support_case, [], [])

    assert result.applicable is False
    assert "authentication or authorization" in result.applicability_reasons[0]


def test_sql_database_playbook_lists_missing_evidence_without_claiming_root_cause() -> None:
    support_case = SupportCase(case_id="case-lock", title="Database is locked", application="Order Management")

    result = evaluate_sql_database_connectivity(support_case, [], [])

    assert result.applicable is True
    assert len(result.missing_evidence) == 5
    assert any("pool" in item.lower() for item in result.missing_evidence)
    assert not any("root cause is" in explanation.lower() for explanation in result.possible_explanations)


def test_playbook_api_declares_sql_database_connectivity_endpoint() -> None:
    from app.api.ui import UI_DIR

    del UI_DIR
    from app.api import playbooks

    route_paths = {route.path for route in playbooks.router.routes}
    assert "/api/cases/{case_id}/playbooks/sql-database-connectivity" in route_paths
