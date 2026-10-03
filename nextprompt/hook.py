"""Fail-open root Stop handler with side-effect-free early exits."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .clipboard import ClipboardAdapter, SystemClipboardAdapter
from .config import ConfigStore
from .output import SuggestionResult, render
from .providers import CodexSuggestionProvider, ProviderUnavailable, SuggestionProvider
from .suggestion import obvious_repeat, sanitize
from .transcript import (
    CodexConversationAdapter,
    ConversationAdapter,
    Message,
    bounded_messages,
    format_context,
)

SETUP_NOTICE = (
    "NextPrompt is installed.\nRecommended:\nEnable automatic clipboard copy.\n"
    "Run:\n$nextprompt-setup"
)


def generate_suggestion(
    messages: list[Message],
    cfg: dict[str, Any],
    store: ConfigStore,
    provider: SuggestionProvider | None = None,
    clipboard: ClipboardAdapter | None = None,
) -> str | None:
    context = bounded_messages(messages, cfg["context"], cfg["privacy"]["redact_secrets"])
    if not context:
        return None
    provider = provider or CodexSuggestionProvider(cfg["model"], store.root)
    text = sanitize(provider.generate(format_context(context)), **cfg["suggestion"])
    if not text or obvious_repeat(text, context):
        return None
    auto_copy = cfg["clipboard"]["auto_copy"] is True
    copied, backend = False, "unavailable"
    if auto_copy:
        try:
            clipboard = clipboard or SystemClipboardAdapter(
                osc52_fallback=cfg["clipboard"]["osc52_fallback"]
            )
            if clipboard.available():
                copied = clipboard.copy(text)
            backend = clipboard.backend_name()
        except Exception:
            copied = False
    selection = getattr(provider, "selection", None)
    result = SuggestionResult(
        text,
        "codex",
        selection.name if selection else cfg["model"]["name"],
        len(context),
        copied,
        backend,
    )
    return render(result, auto_copy)


def handle_stop(
    payload: object,
    *,
    store: ConfigStore | None = None,
    conversation: ConversationAdapter | None = None,
    provider: SuggestionProvider | None = None,
    clipboard: ClipboardAdapter | None = None,
) -> str | None:
    if os.environ.get("NEXTPROMPT_INTERNAL") == "1":
        return None
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "Stop":
        return None
    if payload.get("stop_hook_active") is True:
        return None
    try:
        store = store or ConfigStore()
        cfg = store.load()
        if not cfg["enabled"] or cfg["trigger_mode"] != "every_turn":
            return None
        if cfg["clipboard"]["auto_copy"] is None:
            return SETUP_NOTICE if store.notice_once(".setup-notice") else None
        path = payload.get("transcript_path")
        if not isinstance(path, str) or not path:
            return None
        conversation = conversation or CodexConversationAdapter(cfg["privacy"]["redact_secrets"])
        messages = conversation.read(Path(path))
        return generate_suggestion(messages, cfg, store, provider, clipboard)
    except ProviderUnavailable as exc:
        try:
            if store and store.error_notice(str(exc)):
                return "NextPrompt skipped: suggestion model unavailable."
        except Exception:
            pass
    except Exception:
        # Hook errors must never control the root turn or reveal content.
        pass
    return None
