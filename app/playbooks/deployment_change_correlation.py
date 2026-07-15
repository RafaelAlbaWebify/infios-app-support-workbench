from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_deployment_change_correlation(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    change_signal = any(
        phrase in searchable
        for phrase in (
            "after deployment", "after release", "after change", "recent deployment", "recent release",
            "recent change", "configuration change", "feature flag", "version upgrade", "patch applied",
            "rollback", "change window", "change record", "release correlation",
        )
    )
    applicable = change_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("change_record", "deployment", "release_record", "configuration_change")):
        missing.append("Approved change/deployment record with scope, owner, start/end time, components, and expected outcome")
    if not any(kind in evidence_types for kind in ("incident_timeline", "reproduction_result", "error_message", "monitoring_snapshot")):
        missing.append("Incident timeline showing last known good, first failure, and objective symptom evidence")
    if not any(kind in evidence_types for kind in ("scope_comparison", "version_comparison", "working_example")):
        missing.append("Comparison across changed/unchanged component, version, instance, environment, tenant, or location")
    if not any(kind in evidence_types for kind in ("deployment_validation", "change_validation", "health_check", "test_result")):
        missing.append("Approved deployment validation, health-check, smoke-test, or monitoring evidence")
    if not any(kind in evidence_types for kind in ("rollback_result", "forward_fix_result", "operator_confirmation", "causal_test")):
        missing.append("Authorized causal validation or operator confirmation; timing alone is not proof")

    checks = [
        GuidedCheck(
            check_id="build-change-incident-timeline",
            name="Build an evidence-backed change and incident timeline",
            purpose="Align the approved change window with last known good, first failure, detection, and recovery timestamps.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved change records, deployment logs, monitoring, and incident evidence.",
                "Record absolute timestamps, time zones, component/version scope, owner, and validation outcome.",
                "State temporal overlap as correlation only, not causation.",
            ],
            evidence_to_capture=["change start/end", "last known good", "first failure", "detection", "component/version", "validation"],
        ),
        GuidedCheck(
            check_id="compare-changed-and-unchanged-scope",
            name="Compare changed and unchanged scope",
            purpose="Determine whether the symptom follows the changed component, version, instance, tenant, location, or environment.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Compare approved objective evidence across changed and unchanged scope.",
                "Record version, instance, environment, configuration, traffic path, and outcome differences.",
                "Do not deploy, roll back, toggle flags, or alter configuration to create a comparison.",
            ],
            evidence_to_capture=["version", "instance", "environment", "configuration", "traffic path", "outcome"],
        ),
        GuidedCheck(
            check_id="review-change-validation-evidence",
            name="Review validation and competing explanations",
            purpose="Assess whether validation evidence supports the change hypothesis while preserving alternative explanations.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Review approved smoke tests, health checks, monitoring, error rates, and dependency evidence.",
                "Record evidence supporting and contradicting the change hypothesis.",
                "Require authorization and a runbook for rollback, forward fix, flag, routing, or configuration changes.",
            ],
            evidence_to_capture=["supporting evidence", "contradicting evidence", "validation gaps", "alternative explanations"],
        ),
    ]

    return PlaybookResult(
        playbook_id="deployment-change-correlation",
        title="Deployment or change correlation",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates a deployment, release, configuration, feature-flag, patch, or other change is temporally related to the incident."]
            if applicable
            else ["No specific deployment or change correlation has yet been captured; investigate the primary symptom first."]
        ),
        confirmed_observation_ids=[
            item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The change may have altered code, configuration, schema, dependency behavior, routing, permissions, capacity, or compatibility.",
            "The symptom may follow only part of the changed scope, such as one instance, tenant, region, version, or traffic path.",
            "The timing may be coincidental while an unrelated dependency, data, certificate, capacity, or network condition caused the incident.",
            "Deployment validation may have passed while missing the affected transaction, data shape, permission, load, or environment.",
        ],
        escalation_criteria=[
            "A critical incident starts within the verified change window and follows changed scope.",
            "Objective before/after evidence shows a stable symptom difference aligned with the change.",
            "Deployment validation failed or omitted the affected path.",
            "Rollback, forward fix, configuration, flag, or routing action is being considered and requires authorized ownership.",
        ],
        safety_warnings=[
            "A recent change is context, not proof. Temporal proximity alone must never be recorded as a confirmed explanation.",
            "Do not deploy, roll back, reconfigure, toggle feature flags, change routing, or modify data without an approved runbook, authorization, checkpoint, and validation plan.",
            "Do not mark a change as causal unless evidence supports the mechanism and an operator explicitly confirms the explanation.",
            "Preserve original change records, timestamps, versions, validation results, and incident evidence; do not rewrite history to fit a hypothesis.",
        ],
    )
