"""Conservative secret removal. No logging or persistence."""

from __future__ import annotations

import re

REDACTED = "[REDACTED]"
PATTERNS = [
    # Also redact incomplete blocks before context trimming.
    re.compile(
        r"-----BEGIN (?:[A-Z0-9 ]*PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----"
        r".*?(?:-----END [A-Z0-9 ]+-----|\Z)",
        re.S,
    ),
    re.compile(r"\b(?:sk-ant-|sk-(?:proj-|svcacct-)?)[A-Za-z0-9_-]+"),
    re.compile(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}"),
    re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9_]+"),
    re.compile(r"\bBearer\s+[^\s\"'<>;,]+", re.I),
    re.compile(
        r"\b(?:[A-Z0-9_]*(?:PASSWORD|PASSWD|TOKEN|API_KEY|APIKEY|SECRET)"
        r"[A-Z0-9_]*)\s*[=:]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;}]+)",
        re.I,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]+\."
        r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    ),
]


def redact(text: str) -> str:
    for pattern in PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text
