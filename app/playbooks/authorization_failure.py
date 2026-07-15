from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_authorization_failure(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [
            support_case.title,
            support_case.application,
            support_case.impact,
            support_case.affected_scope,
        ]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    authenticated = any(
        phrase in searchable
        for phrase in (
            "login succeeds",
            "signed in",
            "authenticated",
            "after login",
            "session established",
        )
    )
    authorization_signal = any(
        phrase in searchable
        for phrase in (
            "401",
            "403",
            "access denied",
            "forbidden",
            "not authorized",
            "insufficient permissions",
            "permission denied",
            "role missing",
        )
    )
    pre_login_failure = any(
        phrase in searchable
        for phrase in (
            "cannot log in",
            "login failed",
            "sign-in failed",
            "authentication failed",
            "invalid credentials",
        )
    )
    applicable = authorization_signal and not (pre_login_failure and not authenticated)

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("error_message", "http_observation", "api_response")):
        missing.append("Sanitized 401/403 response, access-denied message, or authorization error")
    if not any(kind in evidence_types for kind in ("reproduction", "reproduction_result")):
        missing.append("Reproduction result with exact resource, operation, and timestamp")
    if not any(kind in evidence_types for kind in ("user_report", "account_context", "role_context")):
        missing.append("Affected account, role, group, and expected access context")
    if not any(kind in evidence_types for kind in ("comparison", "working_example")):
        missing.append("Comparison with an approved working account or role")
    if not any(kind in evidence_types for kind in ("recent_change", "permission_change", "deployment", "change_record")):
        missing.append("Recent role, group, policy, deployment, or permission-change context")

    checks = [
        GuidedCheck(
            check_id="confirm-authenticated-boundary",
            name="Confirm authentication succeeds before access is denied",
            purpose="Separate authorization failure from authentication or general application failure.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Confirm the user reaches an authenticated application state.",
                "Record the exact page, API operation, or business action that is denied.",
                "Capture the sanitized message, HTTP status, timestamp, and correlation identifier when available.",
            ],
            evidence_to_capture=["authenticated state", "resource or operation", "HTTP status", "timestamp", "correlation ID"],
        ),
        GuidedCheck(
            check_id="compare-approved-role",
            name="Compare with an approved account or role",
            purpose="Determine whether access differs by user, role, group, location, or environment.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use only an approved test account or a consenting user with expected access.",
                "Repeat the same read-only navigation or operation.",
                "Record role and group differences without copying credentials, tokens, or session data.",
            ],
            evidence_to_capture=["account type", "role", "group", "environment", "result", "timestamp"],
        ),
        GuidedCheck(
            check_id="review-read-only-entitlement-evidence",
            name="Review entitlement evidence in approved read-only tools",
            purpose="Capture current assignments and policy outcomes without changing access.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only identity, application, or audit views.",
                "Record current role/group assignments, policy result, resource identifier, and relevant timestamps.",
                "Do not add roles, groups, permissions, exceptions, or policy bypasses as part of diagnosis.",
            ],
            evidence_to_capture=["role assignments", "group assignments", "policy result", "resource", "timestamp"],
        ),
    ]

    return PlaybookResult(
        playbook_id="authorization-failure",
        title="Authorization or access-denied failure",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates an authenticated user is denied access to a resource or operation."]
            if applicable
            else ["The current evidence does not yet distinguish authorization failure from login or application failure."]
        ),
        confirmed_observation_ids=[
            item.observation_id
            for item in observations
            if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The affected account may not currently have the expected role or group assignment.",
            "The application may be evaluating a different entitlement, tenant, environment, or resource than expected.",
            "A policy, claim, token scope, or role-mapping result may deny the requested operation.",
            "A recent application, identity, or permission change may be temporally related.",
        ],
        escalation_criteria=[
            "The same expected role is denied for multiple approved users.",
            "A stable 401/403, policy rejection, missing claim, or role-mapping symptom is captured.",
            "The account and entitlement appear correct in approved read-only views, but the application still denies access.",
            "A critical business process is blocked and no approved alternative exists.",
        ],
        safety_warnings=[
            "A 401 or 403 response is evidence of a denied request, not proof of which system or policy is at fault.",
            "Do not add users to groups, grant roles, change claims, alter policies, or bypass access controls without approved authorization.",
            "Never request, retain, or share passwords, MFA codes, tokens, session cookies, or restricted identity data.",
        ],
    )
