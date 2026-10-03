"""Version-isolated conversation parsing; read a bounded tail, never a repository."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .redact import redact

TAIL_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Message:
    role: str
    text: str


class ConversationAdapter(ABC):
    @abstractmethod
    def read(self, path: Path) -> list[Message]:
        """Return visible user/assistant text in chronological order."""


def clean_prose(text: str) -> str:
    text = re.sub(r"```[^\n]*\n.*?(?:```|\Z)", "", text, flags=re.S)
    text = re.sub(
        r"<(environment_context|user_instructions|system_reminder|"
        r"system-reminder|tool_result|reasoning|analysis|hidden_state)\b[^>]*>"
        r".*?(?:</\1>|\Z)",
        "",
        text,
        flags=re.S | re.I,
    )
    # A Codex skill injection is instruction metadata, not a new user request.
    if text.lstrip().startswith(("# AGENTS.md instructions", "<skill>", "<skills_instructions>")):
        return ""
    lines = []
    for line in text.splitlines():
        if re.match(
            r"\s*(?:diff --git|@@ |[+-]{3} |[+-](?!\s)|"
            r"\$ |Traceback |File \"|\{\"|\[\d{4}-|\d{4}-\d\d-\d\d[T ])",
            line,
        ):
            continue
        line = "".join(c for c in line if c in "\t" or ord(c) >= 32)
        if line.strip():
            lines.append(line)
    return "\n".join(lines).strip()


class CodexConversationAdapter(ConversationAdapter):
    def __init__(self, redact_secrets: bool = True) -> None:
        self.redact_secrets = redact_secrets

    def read(self, path: Path) -> list[Message]:
        try:
            with path.open("rb") as stream:
                stream.seek(0, 2)
                offset = max(0, stream.tell() - TAIL_BYTES)
                stream.seek(offset)
                data = stream.read(TAIL_BYTES)
            if offset:
                data = data.partition(b"\n")[2]  # Drop a partial first record.
        except OSError:
            return []
        records: list[dict[str, Any]] = []
        for line in data.splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
            except (ValueError, UnicodeError):
                continue
        # Rollouts can contain both response_item and event_msg copies of the same
        # text. Prefer canonical response items, avoiding duplicate context.
        canonical = any(
            r.get("type") == "response_item"
            and isinstance(r.get("payload"), dict)
            and r["payload"].get("type") == "message"
            for r in records
        )
        messages: list[Message] = []
        for record in records:
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            role, text = "", ""
            if canonical and record.get("type") == "response_item":
                if payload.get("type") != "message":
                    continue
                role = payload.get("role", "")
                if payload.get("channel") in ("analysis", "summary", "justify", "confidence"):
                    continue
                content = payload.get("content", [])
                if not isinstance(content, list):
                    continue
                text = "\n".join(
                    p["text"]
                    for p in content
                    if isinstance(p, dict)
                    and p.get("type") in ("input_text", "output_text", "text")
                    and isinstance(p.get("text"), str)
                )
            elif not canonical and record.get("type") == "event_msg":
                kind = payload.get("type")
                role = {"user_message": "user", "agent_message": "assistant"}.get(kind, "")
                if payload.get("phase") == "analysis":
                    continue
                text = payload.get("message", "")
            if role in ("user", "assistant") and isinstance(text, str):
                prose = clean_prose(redact(text) if self.redact_secrets else text)
                if prose:
                    messages.append(Message(role, prose))
        return messages


def bounded_messages(
    messages: list[Message], limits: dict[str, int], redact_secrets: bool = True
) -> list[Message]:
    """Redact before slicing so clipping cannot reveal a partial credential."""
    chosen: list[Message] = []
    remaining = limits["max_total_chars"]
    for msg in reversed(messages):
        if msg.role not in ("user", "assistant"):
            continue
        text = redact(msg.text) if redact_secrets else msg.text
        text = clean_prose(text)
        if not text:
            continue
        overhead = len(msg.role.upper()) + 3  # ROLE:\ntext\n
        available = min(limits["max_chars_per_message"], remaining - overhead)
        if available <= 0:
            break
        text = text[-available:]
        chosen.append(Message(msg.role, text))
        remaining -= overhead + len(text)
        if len(chosen) >= limits["last_messages"]:
            break
    return list(reversed(chosen))


def format_context(messages: list[Message]) -> str:
    return "".join(f"{m.role.upper()}:\n{m.text}\n" for m in messages)
