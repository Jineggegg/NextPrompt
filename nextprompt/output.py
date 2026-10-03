"""Official Hook JSON and ordinary terminal text; no TUI patches."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SuggestionResult:
    suggestion: str
    provider: str
    model: str
    context_messages: int
    copied: bool
    clipboard_backend: str


def render(result: SuggestionResult, auto_copy: bool) -> str:
    if not auto_copy:
        return f"Next prompt:\n{result.suggestion}"
    text = f"Next → {result.suggestion}"
    if result.copied:
        if result.clipboard_backend.startswith("OSC 52"):
            return text + "\nClipboard copy requested (OSC 52; unverified)."
        return text + "\n✓ Copied to clipboard"
    return text + "\nClipboard unavailable — copy the prompt above manually."


class OutputAdapter(ABC):
    @abstractmethod
    def encode(self, text: str) -> str: ...


class TerminalOutputAdapter(OutputAdapter):
    def encode(self, text: str) -> str:
        return text


class CodexHookOutputAdapter(OutputAdapter):
    def encode(self, text: str) -> str:
        # No decision:block, reason, exit 2, or continue:false. Suggestion only.
        return json.dumps({"systemMessage": text}, ensure_ascii=False)


class GhostTextOutputAdapter(OutputAdapter):
    """Reserved for a future official plugin composer-injection API."""

    def encode(self, text: str) -> str:
        raise NotImplementedError("Codex exposes no plugin ghost-text output contract")
