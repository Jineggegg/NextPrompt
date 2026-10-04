"""Official Hook JSON and ordinary terminal text; no TUI patches."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .i18n import message


@dataclass(frozen=True)
class SuggestionResult:
    suggestion: str
    provider: str
    model: str
    context_messages: int
    copied: bool
    clipboard_backend: str


def render(result: SuggestionResult, auto_copy: bool, language: str = "en") -> str:
    if not auto_copy:
        return f"{message(language, 'display')}\n{result.suggestion}"
    text = f"{message(language, 'next')} {result.suggestion}"
    if result.copied:
        if result.clipboard_backend.startswith("OSC 52"):
            return text + "\n" + message(language, "osc52")
        return text + "\n" + message(language, "copied")
    return text + "\n" + message(language, "unavailable")


def render_copy_status(result: SuggestionResult, language: str = "en") -> str:
    """Copy outcome alone, for prompts the reply already shows."""
    if not result.copied:
        return message(language, "unavailable")
    if result.clipboard_backend.startswith("OSC 52"):
        return message(language, "osc52")
    return message(language, "copied")


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
