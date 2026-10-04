"""Best-effort desktop notification; detached so the hook never waits on it."""

from __future__ import annotations

import os
import shutil
import subprocess

from .platform import PlatformInfo, detect_platform

# Text arrives through environment variables; nothing is interpolated into a script.
_POWERSHELL_TOAST = (
    "$ErrorActionPreference='Stop';"
    "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,"
    "ContentType=WindowsRuntime]|Out-Null;"
    "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
    "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
    "$t=$x.GetElementsByTagName('text');"
    "$t.Item(0).AppendChild($x.CreateTextNode($env:NEXTPROMPT_NOTIFY_TITLE))|Out-Null;"
    "$t.Item(1).AppendChild($x.CreateTextNode($env:NEXTPROMPT_NOTIFY_BODY))|Out-Null;"
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
    "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe')"
    ".Show([Windows.UI.Notifications.ToastNotification]::new($x))"
)
_OSASCRIPT = (
    "on run argv",
    "display notification (item 2 of argv) with title (item 1 of argv)",
    "end run",
)


def notification_command(info: PlatformInfo, title: str, body: str) -> list[str] | None:
    if info.name == "macos" and (osascript := shutil.which("osascript")):
        script = [arg for line in _OSASCRIPT for arg in ("-e", line)]
        return [osascript, *script, title, body]
    if info.name in ("windows", "wsl") and (powershell := shutil.which("powershell.exe")):
        return [powershell, "-NoProfile", "-NonInteractive", "-Command", _POWERSHELL_TOAST]
    if info.name in ("wayland", "x11") and (notify_send := shutil.which("notify-send")):
        return [notify_send, "--app-name=NextPrompt", title, body]
    return None


def send_notification(title: str, body: str, info: PlatformInfo | None = None) -> bool:
    """Start the platform notifier and return immediately; failures are silent."""
    info = info or detect_platform()
    command = notification_command(info, title, body)
    if command is None:
        return False
    env = {**os.environ, "NEXTPROMPT_NOTIFY_TITLE": title, "NEXTPROMPT_NOTIFY_BODY": body}
    if info.name == "wsl":
        # WSL forwards only variables listed in WSLENV to Windows processes.
        shared = "NEXTPROMPT_NOTIFY_TITLE:NEXTPROMPT_NOTIFY_BODY"
        env["WSLENV"] = f"{env['WSLENV']}:{shared}" if env.get("WSLENV") else shared
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        attempts = [{"creationflags": flags | subprocess.CREATE_BREAKAWAY_FROM_JOB}]
        attempts.append({"creationflags": flags})
    else:
        attempts = [{"start_new_session": True}]
    for kwargs in attempts:
        try:
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                close_fds=True,
                **kwargs,
            )
            return True
        except (OSError, ValueError):
            continue
    return False
