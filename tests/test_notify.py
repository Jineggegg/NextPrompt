import subprocess
from unittest.mock import Mock

import pytest

from nextprompt.notify import notification_command, send_notification
from nextprompt.platform import PlatformInfo

TITLE, BODY = "下一句已复制", '运行完整测试；"$(rm -rf ~)" `x` 🚀'


@pytest.fixture
def which(monkeypatch):
    tools = {
        "osascript": "/usr/bin/osascript",
        "powershell.exe": "C:/ps/powershell.exe",
        "notify-send": "/usr/bin/notify-send",
    }
    monkeypatch.setattr("nextprompt.notify.shutil.which", lambda name: tools.get(name))
    return tools


def test_macos_passes_text_as_arguments_not_script(which):
    command = notification_command(PlatformInfo("macos", "macOS"), TITLE, BODY)
    assert command[0] == "/usr/bin/osascript"
    assert command[-2:] == [TITLE, BODY]
    assert all(BODY not in part for part in command[:-2])


@pytest.mark.parametrize("name", ["windows", "wsl"])
def test_windows_reads_text_from_environment(which, name):
    command = notification_command(PlatformInfo(name, name), TITLE, BODY)
    assert command[0] == "C:/ps/powershell.exe"
    assert all(TITLE not in part and BODY not in part for part in command)
    assert "$env:NEXTPROMPT_NOTIFY_BODY" in command[-1]


def test_linux_desktop_uses_notify_send(which):
    command = notification_command(PlatformInfo("wayland", "Linux Wayland"), TITLE, BODY)
    assert command == ["/usr/bin/notify-send", "--app-name=NextPrompt", TITLE, BODY]


def test_headless_or_missing_tool_sends_nothing(which, monkeypatch):
    assert notification_command(PlatformInfo("headless", "SSH/headless"), TITLE, BODY) is None
    monkeypatch.setattr("nextprompt.notify.shutil.which", lambda name: None)
    assert send_notification(TITLE, BODY, PlatformInfo("macos", "macOS")) is False


def test_send_is_detached_and_never_waits(which, monkeypatch):
    popen = Mock()
    monkeypatch.setattr("nextprompt.notify.subprocess.Popen", popen)
    assert send_notification(TITLE, BODY, PlatformInfo("wsl", "WSL")) is True
    kwargs = popen.call_args.kwargs
    assert kwargs["stdout"] is subprocess.DEVNULL and kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["env"]["NEXTPROMPT_NOTIFY_BODY"] == BODY
    assert "NEXTPROMPT_NOTIFY_BODY" in kwargs["env"]["WSLENV"]
    popen.return_value.wait.assert_not_called()


def test_launch_failure_is_silent(which, monkeypatch):
    monkeypatch.setattr("nextprompt.notify.subprocess.Popen", Mock(side_effect=OSError("boom")))
    assert send_notification(TITLE, BODY, PlatformInfo("macos", "macOS")) is False
