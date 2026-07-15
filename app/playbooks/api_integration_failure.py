from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_api_integration_failure(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    integration_signal = any(
        phrase in searchable
        for phrase in (
            "api failure", "integration failure", "webhook failed", "callback failed",
            "invalid payload", "schema validation", "contract mismatch", "unexpected response",
            "downstream api", "upstream api", "message rejected", "queue rejected",
            "400 bad request", "404 not found", "409 conflict", "422 unprocessable",
            "rate limit", "429", "correlation id", "request id",
        )
    )
    availability_signal = any(phrase in searchable for phrase in ("502", "503", "504", "service unavailable", "gateway timeout"))
    access_signal = any(phrase in searchable for phrase in ("401", "403", "invalid token", "access denied", "forbidden"))
    applicable = integration_signal and not availability_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("api_request", "api_response", "http_observation", "integration_error", "error_message")):
        missing.append("Sanitized request/response boundary, status or integration error, timestamp, and correlation identifier")
    if not any(kind in evidence_types for kind in ("reproduction", "reproduction_result", "delivery_result")):
        missing.append("Bounded approved reproduction or delivery result with operation, environment, and timestamp")
    if not any(kind in evidence_types for kind in ("contract", "schema", "mapping", "payload_summary")):
        missing.append("Approved contract, schema, mapping, or sanitized payload-shape evidence")
    if not any(kind in evidence_types for kind in ("scope_comparison", "working_example", "comparison")):
        missing.append("Comparison with a known-good request, version, client, partner, route, or environment")
    if not any(kind in evidence_types for kind in ("recent_change", "deployment", "contract_change", "configuration_change", "change_record")):
        missing.append("Recent deployment, API version, contract, credential, endpoint, routing, or partner-change context")

    checks = [
        GuidedCheck(
            check_id="capture-integration-boundary",
            name="Capture the exact integration boundary",
            purpose="Identify the producer, consumer, operation, protocol, and first observable rejection or unexpected response.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Record the approved operation, method, endpoint label, status, sanitized response, timestamp, duration, API version, and correlation identifier.",
                "Capture payload shape and required-field presence only; remove secrets, tokens, personal data, and restricted business data.",
                "Do not replay mutating requests or callbacks in production unless an approved runbook explicitly permits it.",
            ],
            evidence_to_capture=["producer", "consumer", "operation", "status", "sanitized response", "timestamp", "API version", "correlation ID"],
        ),
        GuidedCheck(
            check_id="compare-contract-and-working-example",
            name="Compare contract and known-good behavior",
            purpose="Determine whether the failure differs by payload shape, API version, client, partner, route, or environment.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved documentation, schemas, mappings, and sanitized known-good samples.",
                "Compare required fields, types, formats, headers, version, and operation without copying credentials or sensitive values.",
                "Use only read-only or non-production validation tools unless production replay is formally authorized.",
            ],
            evidence_to_capture=["contract version", "required fields", "type or format difference", "client or partner", "environment", "result"],
        ),
        GuidedCheck(
            check_id="review-delivery-and-dependency-evidence",
            name="Review approved delivery and dependency evidence",
            purpose="Correlate the failure with retries, rate limits, queue or webhook delivery, dependency status, or response patterns without changing the integration.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only logs, dashboards, delivery histories, queue metrics, or tracing summaries.",
                "Record attempt count, response class, retry or rate-limit signal, delivery state, time window, and correlation identifiers.",
                "Do not purge queues, replay messages, reset offsets, disable validation, alter mappings, rotate credentials, or change endpoints as part of diagnosis.",
            ],
            evidence_to_capture=["attempt count", "response class", "retry or rate-limit signal", "delivery state", "time window", "correlation ID"],
        ),
    ]

    if applicable:
        reasons = ["Evidence indicates an API, webhook, message, contract, mapping, payload, or partner integration failure."]
    elif availability_signal:
        reasons = ["The current evidence points to gateway or service availability; use the service-unavailable playbook first."]
    elif access_signal:
        reasons = ["The current evidence may primarily involve API authentication or authorization rather than an integration contract failure."]
    else:
        reasons = ["The current evidence does not yet distinguish an API/integration failure from application, availability, access, network, or data failure."]

    return PlaybookResult(
        playbook_id="api-integration-failure",
        title="API or integration failure",
        applicable=applicable,
        applicability_reasons=reasons,
        confirmed_observation_ids=[item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The producer and consumer may disagree on API version, schema, required fields, data types, formats, headers, or mapping.",
            "The request may be rejected because of validation, conflict, rate limiting, idempotency, ordering, or partner-side business rules.",
            "A queue, webhook, callback, gateway, DNS, TLS, network, or downstream dependency may interrupt delivery or response handling.",
            "A deployment, endpoint, credential, contract, mapping, or partner change may be temporally related.",
        ],
        escalation_criteria=[
            "Multiple approved requests, clients, partners, routes, or environments reproduce the same contract or delivery failure.",
            "A stable status, validation error, correlation ID, rejected field, version mismatch, rate-limit, or delivery-state signal is captured.",
            "Approved evidence shows repeated delivery failure, incompatible contract behavior, or dependency errors in the same time window.",
            "A critical business process is blocked and no approved alternative integration path exists.",
        ],
        safety_warnings=[
            "An HTTP status, validation message, rejected field, retry, or correlation does not by itself prove which producer, consumer, gateway, dependency, or change is the root cause.",
            "Never collect or expose API keys, bearer tokens, client secrets, signed URLs, cookies, credentials, personal data, or unrestricted production payloads.",
            "Do not replay mutating requests, resend callbacks, purge queues, reset offsets, disable validation, bypass authentication, alter mappings, rotate credentials, or change endpoints without an approved runbook and authorization.",
            "Use bounded read-only or non-production checks and avoid duplicate business transactions or uncontrolled retries.",
        ],
    )
