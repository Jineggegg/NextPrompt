import subprocess

import pytest

from nextprompt.clipboard import SystemClipboardAdapter
from nextprompt.platform import PlatformInfo


@pytest.mark.parametrize(
    ("platform", "commands", "expected"),
    [
        ("windows", {"powershell.exe", "clip.exe"}, "powershell.exe"),
        ("windows", {"clip.exe"}, "clip.exe"),
        ("wsl", {"clip.exe", "powershell.exe"}, "clip.exe"),
        ("wsl", {"powershell.exe"}, "powershell.exe"),
        ("macos", {"pbcopy"}, "pbcopy"),
        ("wayland", {"wl-copy", "xclip", "xsel"}, "wl-copy"),
        ("wayland", {"xclip", "xsel"}, "xclip"),
        ("x11", {"xclip", "xsel"}, "xclip"),
        ("x11", {"xsel"}, "xsel"),
        ("headless", {"xclip"}, "unavailable"),
    ],
)
def test_backend_order(monkeypatch, platform, commands, expected):
    monkeypatch.setattr("nextprompt.clipboard.shutil.which", lambda x: x if x in commands else None)
    adapter = SystemClipboardAdapter(PlatformInfo(platform, platform))
    assert adapter.backend_name() == expected


@pytest.mark.parametrize("platform", ["windows", "wsl", "macos", "wayland", "x11"])
@pytest.mark.parametrize(
    "text",
    [
        "Run the tests.",
        "运行完整测试并检查最终 diff。",
        "检查 CI 后创建 PR。",
        "🚀 中文\nmultiline",
    ],
)
def test_exact_unicode_payload(monkeypatch, platform, text):
    calls = []
    backend = {
        "windows": "powershell.exe",
        "wsl": "clip.exe",
        "macos": "pbcopy",
        "wayland": "wl-copy",
        "x11": "xclip",
    }[platform]
    monkeypatch.setattr("nextprompt.clipboard.shutil.which", lambda x: x if x == backend else None)

    def copy(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr("nextprompt.clipboard.run_process", copy)
    adapter = SystemClipboardAdapter(PlatformInfo(platform, platform))
    assert adapter.copy(text)
    args, kwargs = calls[0]
    encoding = "utf-16le" if platform == "wsl" else "utf-8"
    assert kwargs["input_data"].decode(encoding) == text
    assert text not in " ".join(args)
    assert 0 < kwargs["timeout"] <= 2
    assert kwargs["capture_output"] is False


def test_fallback_after_failure(monkeypatch):
    monkeypatch.setattr("nextprompt.clipboard.shutil.which", lambda name: name)

    def copy(args, **kwargs):
        return subprocess.CompletedProcess(args, int(args[0] == "xclip"), b"", b"")

    monkeypatch.setattr("nextprompt.clipboard.run_process", copy)
    adapter = SystemClipboardAdapter(PlatformInfo("x11", "X11"))
    assert adapter.copy("Run the tests.")
    assert adapter.backend_name() == "xsel"


def test_unavailable_never_installs(monkeypatch):
    monkeypatch.setattr("nextprompt.clipboard.shutil.which", lambda _: None)
    monkeypatch.setattr(
        "nextprompt.clipboard.run_process", lambda *a, **k: pytest.fail("subprocess")
    )
    adapter = SystemClipboardAdapter(PlatformInfo("headless", "headless"))
    assert not adapter.available()
    assert not adapter.copy("Run the tests.")


def test_osc52_off_and_unsupported_terminal(monkeypatch):
    monkeypatch.setattr("nextprompt.clipboard.shutil.which", lambda _: None)
    monkeypatch.setenv("TERM", "dumb")
    assert not SystemClipboardAdapter(PlatformInfo("headless", "headless"), True).available()
    assert not SystemClipboardAdapter(PlatformInfo("headless", "headless")).available()
