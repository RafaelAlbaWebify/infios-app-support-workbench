from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SecretScanFinding:
    kind: str
    location: str
    occurrences: int


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "authorization_header",
        re.compile(r"(?im)^authorization\s*:\s*(?:bearer|basic)\s+(?!\[REDACTED\])\S+"),
    ),
    (
        "cookie_header",
        re.compile(r"(?im)^(?:set-)?cookie\s*:\s*(?!\[REDACTED\]).+$"),
    ),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    ),
    (
        "url_secret",
        re.compile(
            r"(?i)[?&](?:password|passwd|pwd|api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token)="
            r"(?!\[REDACTED\])[^&#\s]+"
        ),
    ),
    (
        "named_secret",
        re.compile(
            r"(?i)(?<![?&])\b(?:password|passwd|pwd|api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|session[_-]?token)"
            r"\s*[:=]\s*(?!\[REDACTED\])[^\s,;]+"
        ),
    ),
    (
        "private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
)


def scan_evidence_content(content: str | dict[str, Any]) -> list[SecretScanFinding]:
    findings: list[SecretScanFinding] = []
    for location, text in _iter_text(content):
        for kind, pattern in _SECRET_PATTERNS:
            occurrences = len(pattern.findall(text))
            if occurrences:
                findings.append(
                    SecretScanFinding(
                        kind=kind,
                        location=location,
                        occurrences=occurrences,
                    )
                )
    return findings


def _iter_text(value: Any, path: str = "content"):
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, dict):
        for key, child in value.items():
            safe_key = str(key).replace(".", "_")
            yield from _iter_text(child, f"{path}.{safe_key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_text(child, f"{path}[{index}]")
