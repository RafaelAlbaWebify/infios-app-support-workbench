from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_authentication_failure(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    authentication_failure = any(
        phrase in searchable
        for phrase in (
            "cannot log in",
            "can't log in",
            "login fails",
            "sign-in fails",
            "signin fails",
            "invalid credentials",
            "authentication failed",
            "mfa failed",
            "account locked",
            "session not established",
        )
    )
    post_login_success = any(
        phrase in searchable
        for phrase in ("login succeeds", "after login", "post-login", "authenticated successfully")
    )
    applicable = authentication_failure and not post_login_success

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("error_message", "user_report", "authentication_result")):
        missing.append("Exact sign-in message or sanitized authentication result")
    if not any(kind in evidence_types for kind in ("reproduction", "reproduction_result")):
        missing.append("Reproduction result with timestamp and affected account type")
    if not any(kind in evidence_types for kind in ("scope_comparison", "user_comparison", "authentication_result")):
        missing.append("Comparison showing whether one user, one role, or multiple users are affected")
    if not any(kind in evidence_types for kind in ("recent_change", "identity_change", "change_record")):
        missing.append("Recent password, MFA, account, federation, or identity-provider change context")

    checks = [
        GuidedCheck(
            check_id="capture-authentication-boundary",
            name="Capture the exact authentication boundary",
            purpose="Confirm whether failure occurs before credentials, during MFA, at token issuance, or when establishing the application session.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Record the last successful step and first failing step.",
                "Capture the exact sanitized message, timestamp, client, and sign-in method.",
            ],
            evidence_to_capture=["timestamp", "client or browser", "sign-in method", "exact sanitized message", "last successful step"],
        ),
        GuidedCheck(
            check_id="compare-approved-account",
            name="Compare with another approved account",
            purpose="Determine whether the symptom is account-specific, role-specific, location-specific, or broader.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use only an approved test account or another consenting affected user.",
                "Do not request or handle another person's password or MFA code.",
            ],
            evidence_to_capture=["account type", "role", "location or network", "timestamp", "result"],
        ),
        GuidedCheck(
            check_id="verify-account-state-read-only",
            name="Verify account and authentication state using approved read-only tools",
            purpose="Capture objective identity evidence without unlocking accounts, resetting passwords, or changing MFA registration.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Check approved read-only sign-in logs or account status views.",
                "Record only sanitized status, failure code, policy name, correlation ID, and timestamp.",
            ],
            evidence_to_capture=["failure code", "account state", "policy or provider", "correlation ID", "timestamp"],
        ),
    ]

    return PlaybookResult(
        playbook_id="authentication-failure",
        title="Authentication or login failure",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates the user cannot establish an authenticated application session."]
            if applicable
            else ["The current evidence does not yet distinguish an authentication failure from a post-login application or authorization problem."]
        ),
        confirmed_observation_ids=[
            item.observation_id
            for item in observations
            if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The account may be locked, disabled, expired, or otherwise unable to authenticate.",
            "MFA, conditional-access, federation, or identity-provider policy may be rejecting the sign-in.",
            "The client may be presenting stale session, cookie, or cached-token state.",
            "A broader identity-provider, network, DNS, certificate, or time-synchronization dependency may be unavailable.",
        ],
        escalation_criteria=[
            "Multiple approved users or locations reproduce the same authentication failure.",
            "A stable failure code, policy rejection, provider error, or correlation ID is captured.",
            "The account state appears valid but authentication still fails across approved clients.",
            "A critical business process is blocked and no approved alternative sign-in path exists.",
        ],
        safety_warnings=[
            "Never request, record, paste, or share passwords, MFA codes, recovery codes, access tokens, refresh tokens, or session cookies.",
            "Do not unlock accounts, reset passwords, modify MFA registration, disable policies, or bypass access controls without an approved runbook and authorization.",
            "A sign-in failure code identifies an observed control decision; it does not by itself prove root cause.",
            "Redact usernames, personal data, device identifiers, IP addresses, and tenant details before external sharing when required.",
        ],
    )
