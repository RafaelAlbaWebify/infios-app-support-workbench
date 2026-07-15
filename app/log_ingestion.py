from __future__ import annotations

import re
from dataclasses import dataclass

MAX_LOG_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class RedactionFinding:
    kind: str
    replacements: int


@dataclass(frozen=True)
class SanitizedLog:
    content: str
    findings: list[RedactionFinding]
    original_bytes: int
    line_count: int


_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "authorization_header",
        re.compile(r"(?im)^(authorization\s*:\s*)(?:bearer|basic)\s+\S+"),
        r"\1[REDACTED]",
    ),
    (
        "cookie_header",
        re.compile(r"(?im)^((?:set-)?cookie\s*:\s*).+$"),
        r"\1[REDACTED]",
    ),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
        "[REDACTED_JWT]",
    ),
    (
        "named_secret",
        re.compile(
            r"(?i)\b(password|passwd|pwd|api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|session[_-]?token)"
            r"(\s*[:=]\s*)([^\s,;]+)"
        ),
        r"\1\2[REDACTED]",
    ),
    (
        "url_secret",
        re.compile(
            r"(?i)([?&](?:password|passwd|pwd|api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token)=)"
            r"([^&#\s]+)"
        ),
        r"\1[REDACTED]",
    ),
)


def sanitize_log_text(text: str) -> SanitizedLog:
    if not isinstance(text, str):
        raise TypeError("Log content must be text.")
    original_bytes = len(text.encode("utf-8"))
    if original_bytes == 0:
        raise ValueError("Log content is empty.")
    if original_bytes > MAX_LOG_BYTES:
        raise ValueError("Log content exceeds the 2 MB limit.")
    if "\x00" in text:
        raise ValueError("Log content appears to be binary.")

    sanitized = text.replace("\r\n", "\n").replace("\r", "\n")
    findings: list[RedactionFinding] = []
    for kind, pattern, replacement in _PATTERNS:
        sanitized, count = pattern.subn(replacement, sanitized)
        if count:
            findings.append(RedactionFinding(kind=kind, replacements=count))

    return SanitizedLog(
        content=sanitized,
        findings=findings,
        original_bytes=original_bytes,
        line_count=sanitized.count("\n") + 1,
    )
