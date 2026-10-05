import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from nextprompt.cli import HOOK_INTERPRETERS, VERSIONED_PYTHONS
from nextprompt.config import ConfigStore
from nextprompt.hook import handle_stop
from nextprompt.output import CodexHookOutputAdapter
from nextprompt.providers import ProviderUnavailable
from nextprompt.transcript import Message

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = {
    "hook_event_name": "Stop",
    "transcript_path": "/fake/session",
    "stop_hook_active": False,
    "session_id": "test-session",
    "turn_id": "test-turn",
    "cwd": "/fake/repo",
    "model": "root-model",
}


def conversation():
    return Mock(
        read=Mock(
            return_value=[
                Message("user", "Fix the login redirect bug."),
                Message("assistant", "Implemented the fix. Targeted tests pass."),
            ]
        )
    )


def test_display_only(configured, provider, clipboard):
    text = handle_stop(
        PAYLOAD,
        store=configured,
        conversation=conversation(),
        provider=provider,
        clipboard=clipboard,
    )
    assert text == "Next prompt:\nRun the full regression suite and review the final diff."
    clipboard.available.assert_not_called()
    clipboard.copy.assert_not_called()
    output = json.loads(CodexHookOutputAdapter().encode(text))
    assert set(output) == {"systemMessage"}


@pytest.mark.parametrize("success", [True, False])
def test_auto_copy_success_and_failure(configured, provider, clipboard, success):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    clipboard.copy.return_value = success
    text = handle_stop(
        PAYLOAD,
        store=configured,
        conversation=conversation(),
        provider=provider,
        clipboard=clipboard,
    )
    clipboard.copy.assert_called_once_with(
        "Run the full regression suite and review the final diff."
    )
    assert "✓ Copied to clipboard" in text if success else "Clipboard unavailable" in text


def test_clipboard_exception_still_displays(configured, provider, clipboard):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    clipboard.copy.side_effect = RuntimeError("DO NOT LOG")
    text = handle_stop(
        PAYLOAD,
        store=configured,
        conversation=conversation(),
        provider=provider,
        clipboard=clipboard,
    )
    assert "Clipboard unavailable" in text
    assert "DO NOT LOG" not in text


@pytest.mark.parametrize("legacy_unset", [False, True])
def test_first_run_copies_and_notifies_without_setup(
    tmp_path, provider, clipboard, notifications, legacy_unset
):
    store = ConfigStore(tmp_path)
    if legacy_unset:
        store.update(lambda cfg: cfg["clipboard"].update(auto_copy=None))
    adapter = conversation()
    text = handle_stop(
        PAYLOAD, store=store, conversation=adapter, provider=provider, clipboard=clipboard
    )
    suggestion = "Run the full regression suite and review the final diff."
    assert text == f"Next → {suggestion}\n✓ Copied to clipboard"
    assert store.path.exists() is legacy_unset
    clipboard.copy.assert_called_once_with(suggestion)
    notifications.assert_called_once_with("Next prompt copied", suggestion)
    assert not (tmp_path / ".setup-notice").exists()


def test_display_only_still_notifies_with_suggestion(configured, provider, notifications):
    handle_stop(PAYLOAD, store=configured, conversation=conversation(), provider=provider)
    notifications.assert_called_once_with(
        "Next prompt", "Run the full regression suite and review the final diff."
    )


def test_notifications_can_be_turned_off(configured, provider, notifications):
    configured.update(lambda cfg: cfg.update(notify=False))
    assert handle_stop(PAYLOAD, store=configured, conversation=conversation(), provider=provider)
    notifications.assert_not_called()


def test_notification_failure_never_hides_the_suggestion(configured, provider, notifications):
    notifications.side_effect = RuntimeError("DO NOT LOG")
    text = handle_stop(PAYLOAD, store=configured, conversation=conversation(), provider=provider)
    assert text == "Next prompt:\nRun the full regression suite and review the final diff."


def test_chinese_notification(configured, provider, clipboard, notifications):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    provider.generate.return_value = "运行完整回归测试，检查最终改动。"
    handle_stop(
        PAYLOAD,
        store=configured,
        conversation=chinese_conversation(),
        provider=provider,
        clipboard=clipboard,
    )
    notifications.assert_called_once_with("下一句已复制", "运行完整回归测试，检查最终改动。")


@pytest.mark.parametrize(
    "error",
    [RuntimeError("SECRET ERROR"), ProviderUnavailable("model"), ProviderUnavailable("timeout")],
)
def test_provider_fail_open_and_cooldown(configured, provider, error):
    provider.generate.side_effect = error
    text = handle_stop(PAYLOAD, store=configured, conversation=conversation(), provider=provider)
    assert text is None or text == "NextPrompt skipped: suggestion model unavailable."
    assert (
        handle_stop(PAYLOAD, store=configured, conversation=conversation(), provider=provider)
        is None
    )


def chinese_conversation():
    return Mock(
        read=Mock(
            return_value=[
                Message("user", "帮我修复登录跳转的问题。"),
                Message("assistant", "已修复，相关测试通过。"),
            ]
        )
    )


def test_labels_follow_the_users_language(configured, provider, clipboard):
    provider.generate.return_value = "运行完整回归测试，检查最终改动。"
    text = handle_stop(
        PAYLOAD, store=configured, conversation=chinese_conversation(), provider=provider
    )
    assert text == "下一句：\n运行完整回归测试，检查最终改动。"
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    text = handle_stop(
        PAYLOAD,
        store=configured,
        conversation=chinese_conversation(),
        provider=provider,
        clipboard=clipboard,
    )
    assert text == "下一句 → 运行完整回归测试，检查最终改动。\n✓ 已复制到剪贴板"
    clipboard.copy.assert_called_once_with("运行完整回归测试，检查最终改动。")


def test_configured_language_overrides_detection(configured, provider):
    configured.update(lambda cfg: cfg.update(language="ja"))
    text = handle_stop(PAYLOAD, store=configured, conversation=conversation(), provider=provider)
    assert text.startswith("次のプロンプト：\n")


def test_skipped_notice_is_localized(configured, provider):
    provider.generate.side_effect = ProviderUnavailable("model")
    text = handle_stop(
        PAYLOAD, store=configured, conversation=chinese_conversation(), provider=provider
    )
    assert text == "NextPrompt 已跳过：建议模型暂不可用。"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {**PAYLOAD, "hook_event_name": "SubagentStop"},
        {**PAYLOAD, "stop_hook_active": True},
    ],
)
def test_non_root_and_continuation_skips(payload, configured, provider):
    adapter = conversation()
    assert handle_stop(payload, store=configured, conversation=adapter, provider=provider) is None
    adapter.read.assert_not_called()
    provider.generate.assert_not_called()


def test_missing_transcript_does_not_infer(configured, provider):
    assert (
        handle_stop({**PAYLOAD, "transcript_path": None}, store=configured, provider=provider)
        is None
    )
    provider.generate.assert_not_called()


@pytest.mark.parametrize(
    "input_bytes",
    [b"", b"bad JSON", b"[]", b"x" * (4 * 1024 * 1024 + 1)],
    ids=["empty", "malformed", "json-array", "oversized"],
)
def test_entrypoint_always_zero(tmp_path, input_bytes):
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks/stop.py")],
        input=input_bytes,
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=3,
    )
    assert result.returncode == 0
    assert result.stdout == b"" and result.stderr == b""


def test_invalid_config_fails_open(tmp_path, provider):
    (tmp_path / "config.json").write_text("{bad")
    assert handle_stop(PAYLOAD, store=ConfigStore(tmp_path), provider=provider) is None
    provider.generate.assert_not_called()


def test_hook_utf8_on_non_utf8_host(tmp_path):
    launcher = (
        "import sys,runpy; "
        f"sys.path.insert(0, {str(ROOT)!r}); "
        "import nextprompt.hook; "
        "nextprompt.hook.handle_stop=lambda _: 'Next prompt:\\n运行完整测试 🚀。'; "
        f"runpy.run_path({str(ROOT / 'hooks/stop.py')!r}, run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", launcher],
        input=json.dumps(PAYLOAD).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path), "PYTHONIOENCODING": "ascii"},
        timeout=3,
    )
    assert result.returncode == 0 and result.stderr == b""
    assert json.loads(result.stdout)["systemMessage"] == "Next prompt:\n运行完整测试 🚀。"


def run_entrypoint(tmp_path, payload, prelude=""):
    launcher = (
        "import sys,runpy; "
        f"sys.path.insert(0, {str(ROOT)!r}); "
        "import nextprompt.hook; "
        "nextprompt.hook.handle_stop=lambda _: 'Next prompt:\\nRun the full suite.'; "
        f"{prelude}"
        f"runpy.run_path({str(ROOT / 'hooks/stop.py')!r}, run_name='__main__')"
    )
    return subprocess.run(
        [sys.executable, "-c", launcher],
        input=payload,
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )


def test_long_final_answer_still_suggests(tmp_path):
    # Codex includes last_assistant_message in the Stop input.
    payload = json.dumps({**PAYLOAD, "last_assistant_message": "长" * 70000}).encode()
    result = run_entrypoint(tmp_path, payload)
    assert result.returncode == 0
    assert json.loads(result.stdout)["systemMessage"] == "Next prompt:\nRun the full suite."


def test_unsupported_python_exits_one_for_fallback(tmp_path):
    # Exit 1 lets `python ... || python3 ...` try the next interpreter; never exit 2.
    result = run_entrypoint(tmp_path, b"{}", prelude="sys.version_info = (3, 8, 18); ")
    assert result.returncode == 1 and result.stdout == b""


def shipped_hook_command():
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
    return hooks["hooks"]["Stop"][0]["hooks"][0]["command"]


def run_shipped_hook(tmp_path, interpreters, old=()):
    """Run the real hooks.json command as Codex does, with only the given commands on PATH.

    Commands in `old` behave like an interpreter older than 3.9: they exit 1.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in old:
        shim = bin_dir / name
        shim.write_text("#!/bin/sh\nexit 1\n")
        shim.chmod(0o755)
    for name in interpreters:
        # The py launcher takes a leading `-3`; its shim drops that argument.
        if os.name == "nt":
            args = "%2 %3" if name == "py" else "%*"
            (bin_dir / f"{name}.cmd").write_text(f'@"{sys.executable}" {args}\r\n')
        else:
            shift = "shift\n" if name == "py" else ""
            shim = bin_dir / name
            shim.write_text(f'#!/bin/sh\n{shift}exec "{sys.executable}" "$@"\n')
            shim.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(bin_dir),
        "PLUGIN_ROOT": str(ROOT),
        "PLUGIN_DATA": str(tmp_path / "data"),
        # Keep the real per-user Python out of the Windows fallback candidates.
        "LOCALAPPDATA": str(tmp_path / "localappdata"),
    }
    if os.name == "nt":
        # Codex runs `%COMSPEC% /C "<command>"` on Windows.
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        args = f'"{comspec}" /D /C "{shipped_hook_command()}"'
    else:
        # Codex runs `$SHELL -lc <command>`; /bin/sh covers the shared syntax.
        args = ["/bin/sh", "-c", shipped_hook_command()]
    return subprocess.run(args, input=b"[]", capture_output=True, env=env, cwd=tmp_path, timeout=10)


@pytest.mark.parametrize(
    "interpreters", [["python"], ["python3"], ["py"]], ids=["python", "python3-only", "py-only"]
)
def test_shipped_hook_command_finds_an_interpreter(tmp_path, interpreters):
    result = run_shipped_hook(tmp_path, interpreters)
    assert result.returncode == 0, result.stderr
    assert result.stdout == b""


def test_shipped_hook_without_python_fails_without_continuing(tmp_path):
    result = run_shipped_hook(tmp_path, [])
    # Codex reports a failed hook; exit code 2 would instead continue the turn.
    assert result.returncode not in (0, 2)


@pytest.mark.skipif(os.name != "nt", reason="Windows default install folders")
@pytest.mark.parametrize(
    "folder", [r"Programs\Python\Python312", r"Python\bin"], ids=["python.org", "pymanager"]
)
def test_shipped_hook_finds_python_off_path_in_default_folder(tmp_path, folder):
    # Codex keeps the PATH it started with: a Python installed afterwards is off PATH.
    target = tmp_path / "localappdata" / folder
    target.parent.mkdir(parents=True)
    base = Path(getattr(sys, "_base_executable", sys.executable)).parent
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(target), str(base)], check=True, capture_output=True
    )
    result = run_shipped_hook(tmp_path, [])
    assert result.returncode == 0, result.stderr
    assert result.stdout == b""


@pytest.mark.skipif(os.name == "nt", reason="python3.X commands are a macOS / Linux convention")
def test_shipped_hook_skips_an_old_python3_for_a_versioned_one(tmp_path):
    result = run_shipped_hook(tmp_path, ["python3.11"], old=["python", "python3"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == b""


def test_every_shipped_hook_tries_the_same_interpreters_in_order():
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
    expected = [" ".join(interpreter) for interpreter in HOOK_INTERPRETERS]
    for event, entries in hooks.items():
        command = entries[0]["hooks"][0]["command"]
        assert [part.split(" -c ")[0] for part in command.split(" || ")] == expected, event


def test_unix_installer_accepts_the_same_versioned_pythons_as_the_hook():
    script = (ROOT / "scripts/install.sh").read_text(encoding="utf-8")
    listed = re.search(r'^versioned_pythons="([^"]*)"$', script, re.MULTILINE).group(1)
    assert tuple(listed.split()) == VERSIONED_PYTHONS


def test_unix_installer_braces_variables_next_to_non_ascii_text():
    # macOS /bin/sh (bash 3.2) reads bytes of a following "…" or "，" as part of the name.
    script = (ROOT / "scripts/install.sh").read_text(encoding="utf-8")
    assert re.findall(r"\$[A-Za-z_]\w*(?=[^\x00-\x7f])", script, re.ASCII) == []
