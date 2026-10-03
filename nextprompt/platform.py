"""Read-only host detection, independently testable."""

from __future__ import annotations

import os
import platform as host_platform
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformInfo:
    name: str
    label: str


def detect_platform(
    system: str | None = None, release: str | None = None, env: Mapping[str, str] | None = None
) -> PlatformInfo:
    env = os.environ if env is None else env
    system = host_platform.system() if system is None else system
    release = host_platform.release() if release is None else release
    if system == "Windows":
        return PlatformInfo("windows", "Windows")
    if system == "Darwin":
        return PlatformInfo("macos", "macOS")
    if system == "Linux":
        if (
            "microsoft" in release.casefold()
            or env.get("WSL_DISTRO_NAME")
            or env.get("WSL_INTEROP")
        ):
            version = "WSL2" if "wsl2" in release.casefold() else "WSL"
            return PlatformInfo("wsl", f"{version} → Windows")
        if env.get("WAYLAND_DISPLAY"):
            return PlatformInfo("wayland", "Linux Wayland")
        if env.get("DISPLAY"):
            return PlatformInfo("x11", "Linux X11")
    return PlatformInfo("headless", "SSH/headless")
