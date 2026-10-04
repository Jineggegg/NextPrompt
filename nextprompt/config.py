"""Plugin-local settings with serialized, atomic updates."""

from __future__ import annotations

import json
import os
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

from .i18n import LANGUAGES
from .redact import redact

# Windows reports a lock file that is still being deleted as "access denied".
LOCK_RETRY_ERRORS: tuple[type[OSError], ...] = (
    (FileExistsError, PermissionError) if os.name == "nt" else (FileExistsError,)
)

DEFAULTS: dict[str, Any] = {
    "version": 1,
    "enabled": True,
    "trigger_mode": "every_turn",
    "language": "auto",
    # "inline": the root model ends its reply with the prompt, which is copied verbatim;
    # "model": a separate lightweight request.
    "source": "inline",
    "clipboard": {"auto_copy": True, "osc52_fallback": False},
    "notify": True,
    "context": {"last_messages": 5, "max_chars_per_message": 2500, "max_total_chars": 8000},
    "model": {"name": "gpt-5.6-luna", "reasoning": "low", "timeout_seconds": 15},
    "suggestion": {"max_words": 20, "max_chars": 240},
    "privacy": {"redact_secrets": True},
}


class ConfigError(ValueError):
    """Invalid settings; never include file contents in the exception."""


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()


def data_directory() -> Path:
    if value := os.environ.get("PLUGIN_DATA"):
        return Path(value).expanduser().resolve()
    # Official legacy plugin directory, required for working hooks in Codex 0.159.
    marketplace = os.environ.get("NEXTPROMPT_MARKETPLACE", "nextprompt")
    return codex_home() / "plugins" / "data" / f"nextprompt-{marketplace}"


def validate_config(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigError("invalid config")
    cfg = deepcopy(DEFAULTS)
    for key, value in raw.items():
        if key not in cfg:
            raise ConfigError("unknown setting")
        if isinstance(cfg[key], dict):
            if not isinstance(value, dict) or set(value) - set(cfg[key]):
                raise ConfigError("invalid settings section")
            cfg[key].update(value)
        else:
            cfg[key] = value
    if type(cfg["version"]) is not int or cfg["version"] != 1:
        raise ConfigError("unsupported version")
    for value in (
        cfg["enabled"],
        cfg["notify"],
        cfg["privacy"]["redact_secrets"],
        cfg["clipboard"]["osc52_fallback"],
    ):
        if type(value) is not bool:
            raise ConfigError("invalid boolean")
    auto = cfg["clipboard"]["auto_copy"]
    if auto is not None and type(auto) is not bool:
        raise ConfigError("invalid clipboard consent")
    if cfg["trigger_mode"] not in ("every_turn", "manual", "code_change_only"):
        raise ConfigError("invalid trigger mode")
    if cfg["source"] not in ("model", "inline"):
        raise ConfigError("invalid suggestion source")
    if cfg["language"] not in ("auto", *LANGUAGES):
        raise ConfigError("invalid language")
    limits = [
        (cfg["context"]["last_messages"], 1, 5),
        (cfg["context"]["max_chars_per_message"], 1, 2500),
        (cfg["context"]["max_total_chars"], 64, 8000),
        (cfg["suggestion"]["max_words"], 1, 20),
        (cfg["suggestion"]["max_chars"], 1, 240),
        (cfg["model"]["timeout_seconds"], 1, 15),
    ]
    if any(type(v) is not int or not lo <= v <= hi for v, lo, hi in limits):
        raise ConfigError("setting exceeds V1 limits")
    name = cfg["model"]["name"]
    if not isinstance(name, str) or not name or len(name) > 100:
        raise ConfigError("invalid model")
    if not all(c.isalnum() or c in "-_.:/" for c in name):
        raise ConfigError("invalid model")
    if redact(name) != name:
        raise ConfigError("invalid model")
    if cfg["model"]["reasoning"] not in ("none", "minimal", "low"):
        raise ConfigError("V1 requires low reasoning")
    return cfg


class ConfigStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root if root is not None else data_directory()
        self.path = self.root / "config.json"

    def load(self) -> dict[str, Any]:
        try:
            if self.path.stat().st_size > 16384:
                raise ConfigError("config too large")
            return validate_config(json.loads(self.path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return deepcopy(DEFAULTS)
        except (ValueError, UnicodeError) as exc:
            raise ConfigError("invalid config") from exc

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = self.root / ".config.lock"
        deadline = time.monotonic() + 2
        while True:
            try:
                fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
                break
            except LOCK_RETRY_ERRORS:
                if time.monotonic() >= deadline:
                    raise ConfigError(
                        "config busy; remove a stale .config.lock if necessary"
                    ) from None
                time.sleep(0.02)
        try:
            yield
        finally:
            lock.unlink(missing_ok=True)

    def update(self, change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        with self._lock():
            cfg = self.load()
            change(cfg)
            cfg = validate_config(cfg)
            fd, name = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=self.root)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as out:
                    json.dump(cfg, out, ensure_ascii=False, indent=2)
                    out.write("\n")
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(name, self.path)
            finally:
                Path(name).unlink(missing_ok=True)
            return cfg

    def notice_once(self, name: str) -> bool:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            fd = os.open(self.root / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            return True
        except FileExistsError:
            return False

    def error_notice(self, category: str) -> bool:
        # Fixed category names only; never exception strings or conversation content.
        if category not in ("model", "timeout", "unavailable", "authentication", "quota"):
            category = "unavailable"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker = self.root / f".error-{category}"
        with self._lock():
            try:
                if time.time() - marker.stat().st_mtime < 3600:
                    return False
            except FileNotFoundError:
                pass
            marker.touch(mode=0o600)
            return True
