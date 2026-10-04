"""Fail-open root Stop handler with side-effect-free early exits."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .clipboard import ClipboardAdapter, SystemClipboardAdapter
from .config import ConfigStore
from .i18n import message, resolve_language
from .notify import send_notification
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


def generate_suggestion(
    messages: list[Message],
    cfg: dict[str, Any],
    store: ConfigStore,
    provider: SuggestionProvider | None = None,
    clipboard: ClipboardAdapter | None = None,
    language: str | None = None,
    notify: bool = False,
) -> str | None:
    context = bounded_messages(messages, cfg["context"], cfg["privacy"]["redact_secrets"])
    if not context:
        return None
    provider = provider or CodexSuggestionProvider(cfg["model"], store.root)
    text = sanitize(provider.generate(format_context(context)), **cfg["suggestion"])
    if not text or obvious_repeat(text, context):
        return None
    # On unless explicitly turned off; legacy unset (None) follows the default.
    auto_copy = cfg["clipboard"]["auto_copy"] is not False
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
    if language is None:
        language = conversation_language(cfg, context)
    if notify:
        # Desktop apps may not show hook messages; this marks the moment to paste.
        try:
            send_notification(message(language, "notify_copied" if copied else "notify"), text)
        except Exception:
            pass
    return render(result, auto_copy, language)


def conversation_language(cfg: dict[str, Any], messages: list[Message]) -> str:
    """Display language: configured, else the latest user message's script."""
    users = (m.text for m in reversed(messages) if m.role == "user")
    return resolve_language(cfg["language"], users)


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
    language = "en"
    try:
        store = store or ConfigStore()
        cfg = store.load()
        if not cfg["enabled"] or cfg["trigger_mode"] != "every_turn":
            return None
        path = payload.get("transcript_path")
        if not isinstance(path, str) or not path:
            return None
        conversation = conversation or CodexConversationAdapter(cfg["privacy"]["redact_secrets"])
        messages = conversation.read(Path(path))
        language = conversation_language(cfg, messages)
        return generate_suggestion(
            messages, cfg, store, provider, clipboard, language, notify=cfg["notify"]
        )
    except ProviderUnavailable as exc:
        try:
            if store and store.error_notice(str(exc)):
                return message(language, "skipped")
        except Exception:
            pass
    except Exception:
        # Hook errors must never control the root turn or reveal content.
        pass
    return None
