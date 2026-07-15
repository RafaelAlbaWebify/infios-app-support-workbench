from __future__ import annotations

import re
from dataclasses import dataclass

MAX_IDENTIFIER_LENGTH = 200


@dataclass(frozen=True)
class CorrelationIdentifier:
    kind: str
    value: str


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "correlation_id",
        re.compile(
            r"(?i)\b(?:x[-_])?correlation[-_]?id\b\s*[:=]\s*[\"']?([A-Za-z0-9][A-Za-z0-9._:/+-]{0,199})"
        ),
    ),
    (
        "request_id",
        re.compile(
            r"(?i)\b(?:x[-_])?request[-_]?id\b\s*[:=]\s*[\"']?([A-Za-z0-9][A-Za-z0-9._:/+-]{0,199})"
        ),
    ),
    (
        "trace_id",
        re.compile(
            r"(?i)\btrace[-_]?id\b\s*[:=]\s*[\"']?([A-Za-z0-9][A-Za-z0-9._:/+-]{0,199})"
        ),
    ),
    (
        "traceparent",
        re.compile(r"(?i)\btraceparent\b\s*[:=]\s*[\"']?([0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2})"),
    ),
)

_REDACTION_MARKERS = {"[REDACTED]", "[REDACTED_JWT]", "REDACTED"}


def extract_correlation_identifiers(text: str) -> list[CorrelationIdentifier]:
    if not isinstance(text, str):
        raise TypeError("Correlation extraction requires text.")

    identifiers: list[CorrelationIdentifier] = []
    seen: set[tuple[str, str]] = set()
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).rstrip(".,;)]}'\"")
            if not value or len(value) > MAX_IDENTIFIER_LENGTH or value.upper() in _REDACTION_MARKERS:
                continue
            key = (kind, value)
            if key in seen:
                continue
            seen.add(key)
            identifiers.append(CorrelationIdentifier(kind=kind, value=value))
    return identifiers
