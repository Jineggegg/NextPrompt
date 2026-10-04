"""Fail-open root Stop handler with side-effect-free early exits."""

from __future__ import annotations

import json
import os
import random
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from .clipboard import ClipboardAdapter, SystemClipboardAdapter
from .config import ConfigStore
from .i18n import INLINE_LABELS, detect_language, go_ahead, message, resolve_language
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
# Repeated with every user message so the root model keeps following the instruction.
INLINE_REMINDER = (
    "NextPrompt: add a suggestion line only for one of the three kinds of step in the "
    "NextPrompt instruction: a part the user named or planned that is not done yet, finishing "
    "or fixing what this turn left unfinished or only diagnosed, or resuming earlier unfinished "
    "work after a side question or small fix. First, if the user is stopping, pausing or "
    'wrapping up ("先这样吧", "that\'s all for now"), write no line, even with parts left. '
    "Otherwise check whether the user named or planned parts (chapters, days, pages, steps) "
    "that are still not done; if so, the line is due, also after long writing. New ideas, "
    "confirmations and answers get no line. "
    "Omit the line when this reply asks the user a question or waits for their choice. "
    "A line is the separate last line: it starts with `→ ` and quotes the user's next prompt "
    "in their language, 「…」 for Chinese and Japanese, “…” otherwise."
)
# One shape per turn, taken in turn per session, so consecutive suggestions never read alike.
STYLE_HINTS: dict[str, tuple[str, ...]] = {
    "zh": (
        # No shape ends in 」。: models then sometimes print a stray 】【 before the 。.
        "要不要「…」？",
        "顺手的话，「…」也能一起做。",
        "还差一步，「…」就齐了。",
        "「…」，需要就说一声。",
        "接下来「…」，怎么样？",
        "想继续的话，说「…」就行。",
        "趁热打铁，「…」？",
        "剩下的就是「…」了。",
        "要接着来的话，「…」随时可以开始。",
        "下一步可以「…」，说一声就开始。",
    ),
    "ja": (
        "「…」はいかがですか。",
        "続けて「…」？",
        "残りは「…」です。",
        "必要なら「…」とどうぞ。",
        "次は「…」でしょうか。",
        "あとは「…」だけです。",
    ),
    "ko": (
        "“…” 할까요?",
        "다음은 “…” 차례예요.",
        "원하시면 “…”라고 말씀해 주세요.",
        "남은 건 “…”예요.",
        "이어서 “…”, 필요하면 말씀하세요.",
    ),
    "en": (
        "Want me to “…”?",
        "One loose end: “…”.",
        "Next up could be “…”.",
        "If you like, “…”.",
        "Say “…” and I'll do it.",
        "Still to do: “…”.",
        "Ready when you are: “…”.",
    ),
}
# Per session, only the position of the last proposed shape is kept.
STYLE_STATE = ".styles.json"
STYLE_SESSIONS = 50
# The line the root model writes: its own words around one quoted prompt, e.g.
# `→ 要不要「给 PDF 加上目录」？`, usually on its own line but sometimes at the end of the
# last paragraph. Optional bold, quote or list markers are formatting.
SUGGESTION_LINE = re.compile(
    r"(?:^\s*(?:[>*_-]\s*)*(?:\*\*|__)?(?:→|->)|(?<=[。！？!?.…])\s*(?:\*\*|__)?→)\s*(.+)$"
)
QUOTED = re.compile(r"「([^「」]+)」|『([^『』]+)』|“([^“”]+)”|\"([^\"]+)\"")
# 「写完《雾中邮局》第四章》: a book title inside sometimes closes the quote with 》.
MISCLOSED = re.compile(r"「([^「」]*《[^「」]*)》")
_LABELS = sorted(
    {label.rstrip(" :：") for label in INLINE_LABELS.values()} | {"下一步", "下一句"},
    key=len,
    reverse=True,
)
# Earlier label format (`下一步建议：…`), still accepted when a model writes it.
INLINE_LINE = re.compile(
    r"^\s*(?:[>*_-]\s*)*(?:" + "|".join(map(re.escape, _LABELS)) + r")(?:\*\*|__)?\s*[:：]"
    r"\s*(?:\*\*|__)?\s*(.+)$",
    re.I,
)
# Models sometimes drop the arrow. A short closing offer that quotes one prompt still
# counts, but only with wording that offers a step, so ordinary sentences with quotes
# never overwrite the clipboard.
OFFER = re.compile(
    r"要不要|需要的话|需要就说|顺手的话|順手的話|继续的话|繼續的話|下一步|接下来「|接下來「|可以接着|"
    r"还差|還差|还没(?:做|写|修|改|处理|完成)|還沒(?:做|寫|修|改|處理|完成)|"
    r"趁热打铁|趁熱打鐵|剩下的就是|接着来的话|接著來的話|就齐了|就齊了|随时可以开始|隨時可以開始|"
    r"说一声就开始|說一聲就開始|怎么样[？?]|怎麼樣[？?]|"
    r"続けて|いかが|必要なら|とどうぞ|残りは|次は「|あとは「|"
    r"다음으로|다음은|이어서|원하시면|필요하면|할까요|차례|남은 건|"
    r"\bwant me to\b|\bshall i\b|\bif you like\b|\bstill to do\b|\bready when you are\b|"
    r"\bnext up\b|\bloose end\b|\bsay “",
    re.I,
)
SENTENCE_END = re.compile(r"[。！？]|[.!?](?=\s)")
INLINE_MAX_CHARS = 500
# Asking the user to choose, confirm or provide something.
ASKS_EXPLICITLY = (
    r"(?:请|請)(?:告诉|告訴|选择|選擇|确认|確認|提供|说明|說明)|告诉我你|告訴我你|你(?:想|希望)(?:让我|讓我)?做|"
    r"(?:哪(?:个|一个|個|一個|种|種|些)|还是|還是)[^。！!\n]{0,30}[?？]|"
    r"\b(?:please (?:choose|confirm|provide|tell me)|tell me (?:which|what)|which (?:one|option) "
    r"(?:do|would) you)\b|\bwhich\b[^.!\n]{0,60}\?|"
    r"教えてください|選んでください|알려 주세요|선택해 주세요"
)
# A reply that ends by asking the user something waits for the user's own answer.
ASKS_USER = re.compile(r"[?？][\s*_`)）」』\"'”’]*$|" + ASKS_EXPLICITLY, re.I)
# After a suggestion line, a trailing question mark is usually content (dialogue in a
# story, a rhetorical line), so only an explicit request for the user's answer counts.
ASKS_USER_EXPLICITLY = re.compile(ASKS_EXPLICITLY, re.I)
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
            "用法 / Use: 有值得做的下一步时，回复末尾会给出一条建议，引号里的指令会复制到剪贴板；"
            "请自行检查、粘贴并发送，插件不会自动发送。 / When a next step is worth it, the "
            "reply ends with a suggestion whose quoted prompt is copied. Review, paste, and "
            "send it yourself; "
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


def _split_suggestion(line: str) -> tuple[str, str | None]:
    """The reply text before a `→` suggestion in this line, and the quoted prompt.

    The prompt is "" when the suggestion quotes nothing and None without a suggestion.
    """
    match = SUGGESTION_LINE.search(line)
    if match:
        quoted = QUOTED.search(match.group(1)) or MISCLOSED.search(match.group(1))
        return line[: match.start()], next(g for g in quoted.groups() if g) if quoted else ""
    # Without the arrow, only the closing sentence can be the offer.
    spans = [m.span() for m in QUOTED.finditer(line)]
    start = 0
    for end in SENTENCE_END.finditer(line.rstrip()[:-1]):
        if not any(a <= end.start() < b for a, b in spans):
            start = end.end()
    sentence = line[start:]
    quotes = list(QUOTED.finditer(sentence))
    if len(quotes) == 1 and len(sentence.strip()) <= 120:
        quote = quotes[0]
        # The offer is in the reply's own words, not in quoted dialogue.
        if OFFER.search(sentence[: quote.start()] + sentence[quote.end() :]):
            return line[:start], next(g for g in quote.groups() if g)
    return line, None


def inline_suggestion(last_reply: object) -> str | None:
    """The prompt the root model suggested at the end of its reply, not rewritten.

    That is the quoted prompt of a final `→` line, or the text after an earlier-style
    `Next prompt:` label. Returns None when the reply suggests nothing and "" when its
    line is unsafe to copy (control characters, credentials, oversized, empty).
    """
    if not isinstance(last_reply, str) or not last_reply.strip():
        return None
    lines = [line for line in last_reply.splitlines() if line.strip()][-3:]
    text = _split_suggestion(lines[-1])[1]
    if text is None:
        labelled = (INLINE_LINE.match(line) for line in reversed(lines))
        match = next((m for m in labelled if m), None)
        if not match:
            return None
        text = match.group(1)
    # Bold or code markers around the whole prompt are formatting.
    text = text.strip().strip("*`").strip()
    if len(text) > INLINE_MAX_CHARS or redact(text) != text:
        return ""
    if any(unicodedata.category(c) in ("Cc", "Cf", "Cs") for c in text):
        return ""
    return text


def asks_user(last_reply: object) -> bool:
    """Whether the reply, apart from any suggestion line, ends by asking the user."""
    if not isinstance(last_reply, str):
        return False
    body = [line for line in last_reply.splitlines() if line.strip()]
    pattern, window = ASKS_USER, 2
    if body:
        before, prompt = _split_suggestion(body[-1])
        if prompt:
            body[-1:] = [before] if before.strip() else []
            # Earlier lines are often written content ("请确认…" in a guide), not a request.
            pattern, window = ASKS_USER_EXPLICITLY, 1
    body = [line for line in body if not INLINE_LINE.match(line)]
    return any(pattern.search(line.strip()) for line in body[-window:])


def _next_style(count: int, session: object, store: ConfigStore | None) -> int:
    """A random shape to start a session, then each next one in turn."""
    if not isinstance(session, str) or not session or store is None:
        return random.randrange(count)
    path = store.root / STYLE_STATE
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    last = state.pop(session, None)
    index = (last + 1) % count if isinstance(last, int) else random.randrange(count)
    state[session] = index
    try:
        store.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, name = tempfile.mkstemp(prefix=".styles-", suffix=".tmp", dir=store.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(dict(list(state.items())[-STYLE_SESSIONS:]), out)
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)
    except OSError:
        # A lost update only risks repeating a shape.
        pass
    return index


def inline_reminder(
    prompt: object, session: object = None, store: ConfigStore | None = None
) -> str:
    """The per-turn reminder with one suggestion shape, in the user's script."""
    language = detect_language(prompt) if isinstance(prompt, str) else "en"
    hints = STYLE_HINTS.get(language.split("-")[0], STYLE_HINTS["en"])
    # Plain text: a code span around the 「…」 hint made models emit stray brackets.
    hint = hints[_next_style(len(hints), session, store)]
    return (
        f"{INLINE_REMINDER} Many replies get no line. If one of the three kinds applies, word "
        f"the line this time like this, arrow included: → {hint}"
    )


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
        store = store or ConfigStore()
        cfg = store.load()
        if cfg["enabled"] and cfg["trigger_mode"] == "every_turn" and cfg["source"] == "inline":
            if event == "UserPromptSubmit":
                return inline_reminder(payload.get("prompt"), payload.get("session_id"), store)
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
        # Without the reply text, whether the model suggested anything is unknown.
        if cfg["source"] == "inline" and isinstance(last_reply, str):
            text = inline_suggestion(last_reply)
            if text and unhelpful(text):
                return None
            if not text:
                # The model chose not to suggest anything, or its line is unsafe to
                # copy; a fallback suggestion would override either decision.
                return None
            # The prompt is written in the user's language.
            language = resolve_language(cfg["language"], [text])
            return deliver(
                go_ahead(text), cfg, "inline", "root", 1, clipboard, language, cfg["notify"], True
            )
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
