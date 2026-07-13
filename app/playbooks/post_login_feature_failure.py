from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase


class GuidedCheck(BaseModel):
    check_id: str
    name: str
    purpose: str
    safety_level: ActionSafetyLevel
    instructions: list[str]
    evidence_to_capture: list[str]


class PlaybookResult(BaseModel):
    playbook_id: str = "post-login-feature-failure"
    title: str = "Post-login feature failure"
    applicable: bool
    applicability_reasons: list[str] = Field(default_factory=list)
    confirmed_observation_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    recommended_checks: list[GuidedCheck] = Field(default_factory=list)
    possible_explanations: list[str] = Field(default_factory=list)
    escalation_criteria: list[str] = Field(default_factory=list)
    safety_warnings: list[str] = Field(default_factory=list)


def evaluate_post_login_feature_failure(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    login_success = any(
        phrase in searchable
        for phrase in ("login succeeds", "can log in", "after login", "post-login", "authenticated")
    )
    feature_failure = any(
        phrase in searchable
        for phrase in ("page fails", "feature fails", "returns an error", "http 500", "orders page", "opening")
    )
    applicable = login_success and feature_failure

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("reproduction", "reproduction_result")):
        missing.append("Reproduction result with an exact or approximate timestamp")
    if not any(kind in evidence_types for kind in ("http_observation", "api_response", "error_message")):
        missing.append("Error details, HTTP status, or API response")
    if not any(kind in evidence_types for kind in ("recent_change", "deployment", "change_record")):
        missing.append("Recent deployment, configuration, or permission-change context")

    checks = [
        GuidedCheck(
            check_id="confirm-login-stage",
            name="Confirm where the login flow succeeds",
            purpose="Separate authentication failure from a post-login application failure.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Confirm that credentials are accepted.",
                "Record the last page that works and the first operation that fails.",
            ],
            evidence_to_capture=["test time", "last successful page", "first failing operation"],
        ),
        GuidedCheck(
            check_id="compare-another-user",
            name="Compare with another approved test user",
            purpose="Determine whether the symptom is user-specific, role-specific, or broader.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Repeat the same operation with an approved test account.",
                "Record whether the result is the same and whether roles differ.",
            ],
            evidence_to_capture=["account type", "role", "timestamp", "result"],
        ),
        GuidedCheck(
            check_id="capture-request-boundary",
            name="Capture the failing request boundary",
            purpose="Identify the endpoint, response status, timestamp, and correlation identifier.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved browser or API evidence tools.",
                "Capture only sanitized request and response details.",
            ],
            evidence_to_capture=["method", "endpoint", "status", "latency", "correlation ID"],
        ),
    ]

    return PlaybookResult(
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates login succeeds before a page, feature, or operation fails."]
            if applicable
            else ["The current evidence does not yet prove both successful login and a post-login feature failure."]
        ),
        confirmed_observation_ids=[
            item.observation_id
            for item in observations
            if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "A user- or role-specific authorization difference may affect the feature.",
            "The application endpoint may be returning an internal error.",
            "A downstream dependency or SQL operation may be failing or timing out.",
            "A recent deployment or configuration change may be temporally related.",
        ],
        escalation_criteria=[
            "The issue reproduces for multiple approved users.",
            "HTTP 5xx, repeated exception, dependency timeout, or SQL symptom is captured.",
            "The business process is blocked and no approved workaround exists.",
        ],
        safety_warnings=[
            "A recent change or SQL error is evidence, not proof of root cause.",
            "Do not restart production services, modify data, permissions, or configuration without an approved runbook or escalation.",
            "Redact credentials, tokens, personal data, and restricted business information before sharing evidence.",
        ],
    )
