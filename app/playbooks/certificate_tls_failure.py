from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_certificate_tls_failure(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    tls_signal = any(
        phrase in searchable
        for phrase in (
            "certificate expired", "certificate not trusted", "certificate verify failed", "hostname mismatch",
            "tls handshake", "ssl handshake", "unable to get local issuer", "unknown ca", "self signed certificate",
            "certificate chain", "certificate revoked", "protocol version", "cipher mismatch", "mutual tls", "mtls",
        )
    )
    access_signal = any(phrase in searchable for phrase in ("invalid credentials", "access denied", "forbidden", "not authorized"))
    applicable = tls_signal and not access_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("tls_error", "certificate_error", "error_message", "connection_error")):
        missing.append("Exact sanitized TLS or certificate error with timestamp and affected endpoint")
    if not any(kind in evidence_types for kind in ("certificate_metadata", "certificate_chain", "handshake_result")):
        missing.append("Approved read-only certificate metadata: subject, issuer, SAN, validity, chain, protocol, and cipher")
    if not any(kind in evidence_types for kind in ("scope_comparison", "client_comparison", "working_example")):
        missing.append("Comparison across client, location, endpoint, environment, or known-good connection")
    if not any(kind in evidence_types for kind in ("time_status", "dns_result", "network_path", "dependency_status")):
        missing.append("Approved read-only client time, DNS, path, proxy, load-balancer, and dependency evidence")
    if not any(kind in evidence_types for kind in ("recent_change", "certificate_change", "deployment", "change_record")):
        missing.append("Recent certificate renewal, trust-store, endpoint, proxy, load-balancer, DNS, or deployment context")

    checks = [
        GuidedCheck(
            check_id="capture-tls-boundary",
            name="Capture the exact TLS failure boundary",
            purpose="Identify the endpoint, client, timestamp, protocol stage, and exact sanitized validation error.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved browser, application, operating-system, or monitoring evidence.",
                "Record endpoint label, timestamp, client, environment, error text, and correlation identifier.",
                "Do not bypass certificate validation or accept an untrusted certificate.",
            ],
            evidence_to_capture=["endpoint", "timestamp", "client", "environment", "error", "correlation ID"],
        ),
        GuidedCheck(
            check_id="inspect-public-certificate-metadata",
            name="Inspect approved certificate and handshake metadata",
            purpose="Compare the presented identity, chain, validity, protocol, and cipher with the expected service contract.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only certificate viewers or diagnostic outputs.",
                "Record subject, issuer, SAN, not-before/not-after, chain result, protocol, and cipher without private keys.",
                "Compare client time and hostname with the certificate identity.",
            ],
            evidence_to_capture=["subject", "issuer", "SAN", "validity", "chain", "protocol", "cipher", "client time"],
        ),
        GuidedCheck(
            check_id="compare-tls-scope",
            name="Compare scope and known-good paths",
            purpose="Determine whether the failure is client-, network-, endpoint-, certificate-, or environment-specific.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Compare approved clients, locations, endpoints, environments, and known-good timestamps.",
                "Record DNS target, proxy or load-balancer path, certificate fingerprint, and outcome differences.",
                "Do not change trust stores, certificates, bindings, protocols, ciphers, DNS, or routing.",
            ],
            evidence_to_capture=["scope", "DNS target", "path", "fingerprint", "outcome"],
        ),
    ]

    return PlaybookResult(
        playbook_id="certificate-tls-failure",
        title="Certificate or TLS failure",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates certificate validation, identity, chain, validity, protocol, cipher, or TLS-handshake failure."]
            if applicable
            else ["The current evidence does not yet distinguish a certificate/TLS failure from access, availability, DNS, or network failure."]
        ),
        confirmed_observation_ids=[
            item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The presented certificate may be expired, not yet valid, revoked, untrusted, incomplete, or issued for a different hostname.",
            "A proxy, load balancer, gateway, or alternate endpoint may be presenting a different certificate or chain.",
            "Client time, trust-store contents, TLS protocol, cipher support, SNI, or mutual-TLS identity may differ.",
            "A renewal, binding, DNS, routing, deployment, or certificate-distribution change may be temporally related.",
        ],
        escalation_criteria=[
            "A production endpoint presents an expired, revoked, mismatched, or untrusted certificate.",
            "Multiple clients or locations reproduce the same handshake failure.",
            "A chain, protocol, cipher, SNI, or mutual-TLS mismatch is captured with approved evidence.",
            "The incident blocks a critical integration or user workflow and no approved alternative exists.",
        ],
        safety_warnings=[
            "A certificate error, fingerprint, or recent renewal is evidence; it does not by itself prove which component is misconfigured.",
            "Never collect or share private keys, certificate passwords, client secrets, tokens, session data, or unrestricted internal endpoint details.",
            "Do not bypass validation, install trust anchors, replace certificates, alter bindings, enable weak protocols or ciphers, or change DNS/routing without an approved runbook and authorization.",
            "Do not export private-key material or use production certificates in uncontrolled diagnostic tools.",
        ],
    )
