"""Fail-open root Stop handler with side-effect-free early exits."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from .clipboard import ClipboardAdapter, SystemClipboardAdapter
from .config import ConfigStore
from .i18n import INLINE_LABELS, message, resolve_language
from .notify import send_notification
from .output import SuggestionResult, render, render_copy_status
from .providers import CodexSuggestionProvider, ProviderUnavailable, SuggestionProvider
from .redact import redact
from .suggestion import obvious_repeat, sanitize, unhelpful
from .transcript import (
    CodexConversationAdapter,
    ConversationAdapter,
    Message,
    bounded_messages,
    format_context,
)

INLINE_PATH = Path(__file__).with_name("inline.txt")
# Repeated with every user message so the root model keeps writing the line.
INLINE_REMINDER = (
    "NextPrompt: end this reply with the next-step line from the NextPrompt instruction, "
    "with its label and suggestion in the language the user writes in "
    "(for example `Next prompt: …`, `下一步建议：…`, `次のプロンプト：…`), typos fixed. "
    "Omit the line when this reply asks the user a question or waits for their choice."
)
_LABELS = sorted(
    {label.rstrip(" :：") for label in INLINE_LABELS.values()} | {"下一步", "下一句"},
    key=len,
    reverse=True,
)
# The line the root model writes under the inline instruction. Optional bold, quote
# or list markers are formatting, not part of the prompt.
INLINE_LINE = re.compile(
    r"^\s*(?:[>*_-]\s*)*(?:" + "|".join(map(re.escape, _LABELS)) + r")(?:\*\*|__)?\s*[:：]"
    r"\s*(?:\*\*|__)?\s*(.+)$",
    re.I,
)
INLINE_MAX_CHARS = 500
# A reply that ends by asking the user something waits for the user's own answer.
ASKS_USER = re.compile(
    r"[?？][\s*_`)）」』\"'”’]*$|"
    r"(?:请|請)(?:告诉|告訴|选择|選擇|确认|確認|提供|说明|說明)|告诉我你|告訴我你|你(?:想|希望)(?:让我|讓我)?做|"
    r"\b(?:please (?:choose|confirm|provide|tell me)|tell me (?:which|what)|which (?:one|option) "
    r"(?:do|would) you)\b|教えてください|選んでください|알려 주세요|선택해 주세요",
    re.I,
)
WELCOME_MARKER = ".welcome-v1"


def first_run_report(payload: object, *, store: ConfigStore | None = None) -> str | None:
    """Show onboarding once, on the first trusted root SessionStart hook."""
    if os.environ.get("NEXTPROMPT_INTERNAL") == "1":
        return None
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "SessionStart":
        return None
    try:
        store = store or ConfigStore()
        cfg = store.load()
        if not cfg["enabled"] or not store.notice_once(WELCOME_MARKER):
            return None
        copy = "开 / on" if cfg["clipboard"]["auto_copy"] is not False else "关 / off"
        notify = "开 / on" if cfg["notify"] else "关 / off"
        return (
            "NextPrompt 安装完成，已就绪 / Installed and ready.\n"
            "用法 / Use: 每轮回复结束后会给出一条下一步建议；请自行检查、粘贴并发送，"
            "插件不会自动发送。 / Review, paste, and send the suggestion yourself; "
            "it is never sent automatically.\n"
            f"当前设置 / Current: 自动复制到剪贴板 / auto-copy {copy}；"
            f"桌面通知 / desktop notification {notify}（默认均开启 / both on by default）。\n"
            "关闭通知 / Turn notifications off: 使用 $nextprompt-setup 并说“关闭通知” "
            "/ use $nextprompt-setup and ask to turn notifications off."
        )
    except Exception:
        # Onboarding must never interrupt the session or expose configuration content.
        return None


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
    selection = getattr(provider, "selection", None)
    model = selection.name if selection else cfg["model"]["name"]
    if language is None:
        language = conversation_language(cfg, context)
    return deliver(text, cfg, "codex", model, len(context), clipboard, language, notify)


def deliver(
    text: str,
    cfg: dict[str, Any],
    provider: str,
    model: str,
    context_messages: int,
    clipboard: ClipboardAdapter | None,
    language: str,
    notify: bool,
    inline: bool = False,
) -> str | None:
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
    result = SuggestionResult(text, provider, model, context_messages, copied, backend)
    if notify:
        # Desktop apps may not show hook messages; this marks the moment to paste.
        try:
            send_notification(message(language, "notify_copied" if copied else "notify"), text)
        except Exception:
            pass
    if inline:
        # The reply already shows the prompt; only report the copy outcome.
        return render_copy_status(result, language) if auto_copy else None
    return render(result, auto_copy, language)


def inline_suggestion(last_reply: object) -> str | None:
    """The root model's own `Next prompt:` line, exactly as the reply shows it.

    The clipboard must match the visible line, so the text is not rewritten. Returns
    None when the reply has no such line and "" when its line is unsafe to copy
    (control characters, credentials, oversized).
    """
    if not isinstance(last_reply, str) or not last_reply.strip():
        return None
    lines = [line for line in last_reply.splitlines() if line.strip()][-3:]
    for line in reversed(lines):
        if match := INLINE_LINE.match(line):
            # Bold or code markers around the whole prompt are formatting.
            text = match.group(1).strip().strip("*`").strip()
            if len(text) > INLINE_MAX_CHARS or redact(text) != text:
                return ""
            if any(unicodedata.category(c) in ("Cc", "Cf", "Cs") for c in text):
                return ""
            return text
    return None


def asks_user(last_reply: object) -> bool:
    """Whether the reply, apart from any next-step line, ends by asking the user."""
    if not isinstance(last_reply, str):
        return False
    body = [
        line for line in last_reply.splitlines() if line.strip() and not INLINE_LINE.match(line)
    ]
    return any(ASKS_USER.search(line.strip()) for line in body[-2:])


def handle_context(payload: object, *, store: ConfigStore | None = None) -> str | None:
    """Inline mode: developer context asking the root model to end with the line.

    SessionStart (also after compaction) carries the full instruction; each user
    prompt adds a one-line reminder so the line is written every turn.
    """
    if os.environ.get("NEXTPROMPT_INTERNAL") == "1":
        return None
    if not isinstance(payload, dict):
        return None
    event = payload.get("hook_event_name")
    if event not in ("SessionStart", "UserPromptSubmit"):
        return None
    try:
        cfg = (store or ConfigStore()).load()
        if cfg["enabled"] and cfg["trigger_mode"] == "every_turn" and cfg["source"] == "inline":
            if event == "UserPromptSubmit":
                return INLINE_REMINDER
            return INLINE_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return None


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
        last_reply = payload.get("last_assistant_message")
        if asks_user(last_reply):
            # Only the user can answer; a suggested prompt would make the assistant
            # ask again and loop.
            return None
        if cfg["source"] == "inline":
            text = inline_suggestion(last_reply)
            if text and unhelpful(text):
                return None
            if text:
                # The prompt is written in the user's language.
                language = resolve_language(cfg["language"], [text])
                return deliver(
                    text, cfg, "inline", "root", 1, clipboard, language, cfg["notify"], True
                )
            if text is not None:
                # The reply shows a line that is unsafe to copy; never copy anything else.
                return None
            # No line at all: fall back to the separate suggestion model below.
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
