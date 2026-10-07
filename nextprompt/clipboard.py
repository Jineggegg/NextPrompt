"""Opt-in clipboard adapters. Never install a backend or interpolate model text."""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path

from .platform import PlatformInfo, detect_platform
from .process import run_process


class ClipboardAdapter(ABC):
    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def copy(self, text: str) -> bool: ...

    @abstractmethod
    def backend_name(self) -> str: ...


class SystemClipboardAdapter(ClipboardAdapter):
    def __init__(self, info: PlatformInfo | None = None, osc52_fallback: bool = False) -> None:
        self.info = info or detect_platform()
        candidates = {
            "windows": [
                ("powershell.exe", "powershell"),
                ("pwsh", "powershell"),
                ("clip.exe", "utf16"),
            ],
            "wsl": [("clip.exe", "utf16"), ("powershell.exe", "powershell")],
            "macos": [("pbcopy", "utf8")],
            "wayland": [("wl-copy", "utf8"), ("xclip", "xclip"), ("xsel", "xsel")],
            "x11": [("xclip", "xclip"), ("xsel", "xsel")],
        }.get(self.info.name, [])
        if self.info.name == "wsl":
            # WSLg shares its Linux clipboard with Windows even when .exe interop
            # is disabled. Only try these when a display is actually configured.
            if os.environ.get("WAYLAND_DISPLAY"):
                candidates += [("wl-copy", "utf8")]
            if os.environ.get("DISPLAY"):
                candidates += [("xclip", "xclip"), ("xsel", "xsel")]
        self.backends = [(path, kind) for name, kind in candidates if (path := shutil.which(name))]
        self.osc52 = osc52_fallback and self._osc52_capable()
        self._used: str | None = None

    @staticmethod
    def _osc52_capable() -> bool:
        # No guessed support through multiplexers; /dev/tty is unavailable on Windows.
        term = os.environ.get("TERM", "")
        return (
            os.name == "posix"
            and not os.environ.get("TMUX")
            and not term.startswith("screen")
            and term.startswith(("xterm", "foot", "wezterm", "alacritty"))
            and Path("/dev/tty").exists()
            and os.isatty(2)
        )

    def available(self) -> bool:
        return bool(self.backends or self.osc52)

    def backend_name(self) -> str:
        if self._used:
            return self._used
        if self.backends:
            return Path(self.backends[0][0]).name
        return "OSC 52 (best effort)" if self.osc52 else "unavailable"

    def copy(self, text: str) -> bool:
        if len(text.encode("utf-8")) > 4096:
            return False
        deadline = time.monotonic() + 2
        for executable, kind in self.backends:
            args = [executable]
            payload = text.encode("utf-16le" if kind == "utf16" else "utf-8")
            if kind == "powershell":
                args += [
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "$ErrorActionPreference='Stop';"
                    "[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false);"
                    "$text=[Console]::In.ReadToEnd();Set-Clipboard -Value $text",
                ]
            elif kind == "xclip":
                args += ["-selection", "clipboard"]
            elif kind == "xsel":
                args += ["--clipboard", "--input"]
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                result = run_process(
                    args, input_data=payload, timeout=remaining, capture_output=False
                )
                if result.returncode == 0:
                    self._used = Path(executable).name
                    return True
            except (OSError, subprocess.TimeoutExpired):
                continue
        if self.osc52:
            try:
                encoded = base64.b64encode(text.encode("utf-8"))
                with open("/dev/tty", "wb", buffering=0) as tty:
                    tty.write(b"\x1b]52;c;" + encoded + b"\x07")
                self._used = "OSC 52 (best effort)"
                # Terminals do not acknowledge clipboard writes; never claim verification.
                return True
            except OSError:
                pass
        return False
