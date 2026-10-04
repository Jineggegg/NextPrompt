"""Convert model text into one bounded, useful instruction."""

from __future__ import annotations

import re
import unicodedata

from .redact import redact
from .transcript import Message

GENERIC = {
    "continue",
    "keep working",
    "proceed",
    "check your work",
    "do more testing",
    "fix the issue",
    "continue working",
    "run tests",
    "do the next step",
    "yes",
    "no",
    "done",
    "okay",
    "ok",
    "next",
    "suggestion",
    "null",
    "none",
    "继续",
    "继续工作",
    "检查工作",
    "修复问题",
}


def sanitize(raw: str, max_words: int = 20, max_chars: int = 240) -> str | None:
    if not isinstance(raw, str) or len(raw) > 16384:
        return None
    text = raw.strip()
    text = re.sub(r"^```[^\n]*\n?", "", text)
    text = text.replace("```", "").strip()
    text = re.sub(r"^\s*(?:suggestion|next prompt|next|prompt)\s*[:→]\s*", "", text, flags=re.I)
    text = text.strip(" \t\r\n\"'“”‘’`")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    text = re.sub(r"^(?:[-*]\s+|\d+[.)]\s+)", "", lines[0])
    text = re.split(r"(?<=[.!?。！？])\s+|(?<=[。！？])(?=\S)", text)[0].strip()
    text = text.strip(" \t\"'“”‘’`")
    # Reject control/format characters rather than hiding malicious terminal output.
    if any(unicodedata.category(c) in ("Cc", "Cf", "Cs") for c in text):
        return None
    if redact(text) != text:
        return None
    if not text or len(text) > min(240, max_chars) or len(text.split()) > min(20, max_words):
        return None
    # Chinese, Japanese and Korean pack a full instruction into few characters/spaces.
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]", text):
        if len(text) < 4:
            return None
    elif len(text) < 8 or len(text.split()) < 3:
        return None
    if text.casefold().strip(" .!。！？") in GENERIC:
        return None
    if re.search(
        r"[{}<>`]|https?://|^#{1,6}\s|^I (?:have|will|can)\b|"
        r"^(?:here is|here's|as an ai|the next prompt is)\b",
        text,
        re.I,
    ):
        return None
    if not any(c.isalpha() for c in text):
        return None
    return text


def obvious_repeat(suggestion: str, context: list[Message]) -> bool:
    last = next((m.text for m in reversed(context) if m.role == "assistant"), "")
    pairs = (
        (
            r"(?:full regression|regression suite).*?(?:pass|green|complete)",
            r"^(?:run|rerun|execute)\b.*?\b(?:regression|full test)",
        ),
        (r"targeted tests.*?(?:pass|green|complete)", r"^(?:run|rerun)\b.*?targeted tests"),
        (
            r"(?:PR\s*#?\d+|pull request).*?(?:created|opened)|created.*?pull request",
            r"^(?:create|open)\b.*?pull request",
        ),
        (
            r"(?:CI|continuous integration).*?(?:pass|green|succeed)",
            r"^(?:check|wait for)\b.*?\bCI\b.*?(?:results|complete|finish)",
        ),
    )
    return any(
        re.search(done, last, re.I | re.S) and re.search(action, suggestion, re.I)
        for done, action in pairs
    )
