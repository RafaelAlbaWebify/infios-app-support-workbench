from __future__ import annotations

from app.domain.models import ActionSafetyLevel, EvidenceItem, Observation, SupportCase
from app.playbooks.post_login_feature_failure import GuidedCheck, PlaybookResult


def evaluate_file_transfer_import_export_failure(
    support_case: SupportCase,
    evidence: list[EvidenceItem],
    observations: list[Observation],
) -> PlaybookResult:
    searchable = " ".join(
        [support_case.title, support_case.application, support_case.impact, support_case.affected_scope]
        + [str(item.content) for item in evidence]
        + [item.statement for item in observations]
    ).lower()

    transfer_signal = any(
        phrase in searchable
        for phrase in (
            "file transfer", "sftp", "ftp", "ftps", "scp", "import failed", "export failed",
            "file not received", "file not delivered", "file rejected", "invalid file", "bad filename",
            "checksum mismatch", "partial file", "zero byte file", "archive corrupt", "decryption failed",
            "permission denied on folder", "landing folder", "inbound file", "outbound file",
        )
    )
    access_signal = any(
        phrase in searchable
        for phrase in ("invalid credentials", "authentication failed", "401", "403", "not authorized")
    )
    applicable = transfer_signal and not access_signal

    evidence_types = {item.evidence_type.lower() for item in evidence}
    missing: list[str] = []
    if not any(kind in evidence_types for kind in ("transfer_status", "import_result", "export_result", "error_message", "file_metadata")):
        missing.append("Sanitized transfer/import/export status, exact error, or file metadata")
    if not any(kind in evidence_types for kind in ("reproduction_result", "transfer_history", "processing_history")):
        missing.append("Transfer or processing history with timestamps, direction, endpoint, and outcome")
    if not any(kind in evidence_types for kind in ("file_comparison", "working_example", "scope_comparison")):
        missing.append("Comparison with an approved successful file, endpoint, partner, environment, or run")
    if not any(kind in evidence_types for kind in ("checksum", "file_properties", "schema_validation", "directory_status")):
        missing.append("Approved read-only filename, size, checksum, format, schema, and directory evidence")
    if not any(kind in evidence_types for kind in ("recent_change", "configuration_change", "certificate_change", "change_record")):
        missing.append("Recent endpoint, certificate, key, permission, naming, format, schedule, or mapping-change context")

    checks = [
        GuidedCheck(
            check_id="capture-transfer-boundary",
            name="Capture the exact transfer and processing boundary",
            purpose="Identify whether failure occurs before transfer, during transport, at landing, validation, import/export, or downstream acknowledgement.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only transfer history, logs, directory listings, and processing status views.",
                "Record direction, endpoint label, filename, sanitized path, timestamp, size, status, error code, and correlation identifier.",
                "Do not retransmit, rename, move, delete, decrypt, extract, or reprocess the production file during diagnosis.",
            ],
            evidence_to_capture=["direction", "endpoint", "filename", "sanitized path", "timestamp", "size", "status", "error code", "correlation ID"],
        ),
        GuidedCheck(
            check_id="compare-file-and-scope",
            name="Compare file properties and affected scope",
            purpose="Determine whether the symptom is specific to one file, partner, endpoint, directory, format, environment, or processing run.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Compare metadata only with an approved successful example.",
                "Record naming pattern, extension, size, checksum, encoding, delimiter, archive/encryption state, endpoint, and outcome differences.",
                "Do not expose file contents or restricted business data unless explicitly approved and minimized.",
            ],
            evidence_to_capture=["naming pattern", "extension", "size", "checksum", "encoding", "format", "encryption state", "endpoint", "outcome"],
        ),
        GuidedCheck(
            check_id="review-read-only-transfer-evidence",
            name="Review endpoint, directory, validation, and downstream evidence",
            purpose="Correlate transport and processing evidence without modifying files, permissions, keys, or jobs.",
            safety_level=ActionSafetyLevel.L1_SAFE,
            instructions=[
                "Use approved read-only endpoint status, directory listing, certificate/key metadata, validation logs, and downstream status views.",
                "Record reachability, directory state, free-space signal, permission result, certificate/key expiry metadata, validation result, and acknowledgement state.",
                "Do not change permissions, rotate keys, replace certificates, clear directories, or rerun imports/exports.",
            ],
            evidence_to_capture=["reachability", "directory state", "capacity signal", "permission result", "certificate/key metadata", "validation result", "acknowledgement"],
        ),
    ]

    return PlaybookResult(
        playbook_id="file-transfer-import-export-failure",
        title="File transfer, import, or export failure",
        applicable=applicable,
        applicability_reasons=(
            ["Evidence indicates a file transfer, landing, validation, import, export, or acknowledgement failure."]
            if applicable
            else ["The current evidence does not yet distinguish a file-transfer or processing failure from access, scheduler, integration, or data-quality failure."]
        ),
        confirmed_observation_ids=[
            item.observation_id for item in observations if item.certainty.value in {"technically_confirmed", "reproduced"}
        ],
        missing_evidence=missing,
        recommended_checks=checks if applicable else checks[:1],
        possible_explanations=[
            "The source may not have produced or delivered the expected file, or transport may have failed before landing.",
            "Filename, path, permission, certificate, key, capacity, network, or endpoint conditions may have blocked transfer or access.",
            "The file may differ in size, checksum, encoding, delimiter, archive, encryption, schema, or naming convention.",
            "Transfer may have succeeded while validation, import/export processing, acknowledgement, or downstream persistence failed.",
        ],
        escalation_criteria=[
            "A critical expected file is overdue, repeatedly rejected, partially delivered, or blocking a business process.",
            "A stable transport error, checksum mismatch, validation failure, permission result, or acknowledgement gap is captured.",
            "Multiple files, partners, endpoints, directories, or environments show the same failure pattern.",
            "No approved alternative delivery or processing path exists.",
        ],
        safety_warnings=[
            "A missing file, transfer status, checksum mismatch, or validation error is evidence; it does not by itself prove which system or party caused the failure.",
            "Do not retransmit, rename, move, delete, overwrite, decrypt, extract, edit, or reprocess production files without an approved runbook and authorization.",
            "Do not change directory permissions, endpoint configuration, certificates, keys, naming rules, schemas, mappings, or schedules during diagnosis.",
            "Never collect passwords or private keys, and redact file contents, personal data, partner details, paths, hostnames, and restricted business information before sharing.",
        ],
    )
