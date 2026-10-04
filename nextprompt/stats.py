"""Local suggestion counts: how often a reply suggests something and whether it is used.

Only counts and short hashes are stored, never prompt or reply text. A suggestion is
matched against the user's next prompt in the same session: sent as is (with or without a
go-ahead such as "，做吧"), sent with more words after it, or not used.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any

from .i18n import GO_AHEAD

STATS_NAME = ".stats.json"
MAX_PENDING = 50
COUNTS = ("replies", "suggested", "exact", "extended", "ignored")


def _norm(text: str) -> str:
    """Ignore case, width, spacing and closing punctuation when comparing prompts."""
    text = re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).casefold())
    return text.rstrip("。.!！?？，,；;~～")


# Any go-ahead, typed or pasted with the copy ("，做吧"), still means "as suggested".
_GO_AHEADS = sorted(
    {_norm(ending) for endings in GO_AHEAD.values() for ending in endings}, key=len, reverse=True
)


def _without_go_ahead(text: str) -> str:
    for ending in _GO_AHEADS:
        if text.endswith(ending):
            return text[: -len(ending)].rstrip(",，、 ")
    return text


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _load(root: Path) -> dict[str, Any]:
    try:
        data = json.loads((root / STATS_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    if not isinstance(data, dict):
        data = {}
    stats: dict[str, Any] = {key: data.get(key) for key in COUNTS}
    for key in COUNTS:
        if type(stats[key]) is not int or stats[key] < 0:
            stats[key] = 0
    pending = data.get("pending")
    stats["pending"] = pending if isinstance(pending, dict) else {}
    return stats


def _save(root: Path, stats: dict[str, Any]) -> None:
    # A lost update between concurrent sessions only skews a count by one.
    stats["pending"] = dict(list(stats["pending"].items())[-MAX_PENDING:])
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, name = tempfile.mkstemp(prefix=".stats-", suffix=".tmp", dir=root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(stats, out)
            os.replace(name, root / STATS_NAME)
        finally:
            Path(name).unlink(missing_ok=True)
    except OSError:
        pass


def record_reply(root: Path, session: object, prompt: str | None) -> None:
    """Count one finished reply and remember its suggestion, if any, as hashes."""
    stats = _load(root)
    stats["replies"] += 1
    key = session if isinstance(session, str) and session else None
    if key:
        stats["pending"].pop(key, None)
    if prompt:
        stats["suggested"] += 1
        if key:
            core = _norm(prompt)
            stats["pending"][key] = {
                "core": _digest(core),
                "length": len(core),
                "time": int(time.time()),
            }
    _save(root, stats)


def record_prompt(root: Path, session: object, prompt: object) -> None:
    """Settle the session's last suggestion against the prompt the user sent next."""
    if not isinstance(session, str) or not session or not isinstance(prompt, str):
        return
    stats = _load(root)
    pending = stats["pending"].pop(session, None)
    if not isinstance(pending, dict):
        return
    text = _without_go_ahead(_norm(prompt))
    length = pending.get("length")
    if _digest(text) == pending.get("core"):
        stats["exact"] += 1
    elif (
        type(length) is int
        and 0 < length < len(text)
        and _digest(text[:length]) == pending.get("core")
    ):
        stats["extended"] += 1
    else:
        stats["ignored"] += 1
    _save(root, stats)


def reset(root: Path) -> None:
    try:
        (root / STATS_NAME).unlink(missing_ok=True)
    except OSError:
        pass


def summary(root: Path) -> list[str]:
    stats = _load(root)
    replies, suggested = stats["replies"], stats["suggested"]
    used = stats["exact"] + stats["extended"]
    decided = used + stats["ignored"]

    def share(part: int, whole: int) -> str:
        return f" ({round(100 * part / whole)}%)" if whole else ""

    return [
        f"Suggestions:      {suggested} of {replies} replies{share(suggested, replies)}",
        f"Used:             {used} of {decided} answered{share(used, decided)}: "
        f"{stats['exact']} as is, {stats['extended']} with more words, "
        f"{stats['ignored']} not used",
    ]
