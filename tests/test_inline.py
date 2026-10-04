import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from nextprompt.config import ConfigError, ConfigStore
from nextprompt.hook import (
    INLINE_PATH,
    INLINE_REMINDER,
    handle_context,
    handle_stop,
    inline_suggestion,
)
from nextprompt.transcript import Message

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = {"hook_event_name": "Stop", "transcript_path": "/fake/session", "stop_hook_active": False}
START = {"hook_event_name": "SessionStart", "source": "startup", "session_id": "s"}
PROMPT = {"hook_event_name": "UserPromptSubmit", "prompt": "fix it", "session_id": "s"}


def reply(last_line):
    return f"Fixed the redirect and the targeted tests pass.\n\n{last_line}"


def test_source_defaults_to_inline_and_validates(tmp_path):
    store = ConfigStore(tmp_path)
    assert store.load()["source"] == "inline"
    with pytest.raises(ConfigError):
        store.update(lambda cfg: cfg.update(source="root"))


def test_context_injects_instruction_and_reminder_by_default(configured):
    text = handle_context(START, store=configured)
    assert text == INLINE_PATH.read_text(encoding="utf-8").strip()
    assert "Next prompt:" in text and "下一步建议：" in text
    assert handle_context(PROMPT, store=configured) == INLINE_REMINDER


@pytest.mark.parametrize(
    "change",
    [
        lambda cfg: cfg.update(enabled=False),
        lambda cfg: cfg.update(trigger_mode="manual"),
        lambda cfg: cfg.update(source="model"),
    ],
)
def test_context_silent_when_off_or_model_mode(configured, change):
    configured.update(change)
    assert handle_context(START, store=configured) is None
    assert handle_context(PROMPT, store=configured) is None


def test_context_ignores_internal_runs_and_other_events(configured, monkeypatch):
    assert handle_context({**START, "hook_event_name": "Stop"}, store=configured) is None
    assert handle_context("not a dict", store=configured) is None
    monkeypatch.setenv("NEXTPROMPT_INTERNAL", "1")
    assert handle_context(START, store=configured) is None


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Next prompt: Add a regression test for logout.", "Add a regression test for logout."),
        ("**Next prompt:** Add a logout test", "Add a logout test"),
        ("> Next prompt：Add a logout test", "Add a logout test"),
        ("下一步建议：运行完整回归测试，检查最终改动。", "运行完整回归测试，检查最终改动。"),
        ("**下一步建议：** `pytest -q`", "pytest -q"),
        # Copied as written: generic or multi-sentence text is not rewritten.
        ("下一步建议：继续", "继续"),
        ("Next prompt: Merge it. Then tag the release.", "Merge it. Then tag the release."),
    ],
)
def test_extracts_the_visible_text(line, expected):
    assert inline_suggestion(reply(line)) == expected


@pytest.mark.parametrize("text", [None, "", "All done, nothing else to do."])
def test_no_line(text):
    assert inline_suggestion(text) is None


UNSAFE = [
    "Next prompt: rotate sk-abcdefghijklmnopqrstuvwxyz0123456789 now",
    "Next prompt: bad \x1b[31m escape",
    "Next prompt: " + "x" * 501,
    "Next prompt: **",
]


@pytest.mark.parametrize("text", UNSAFE)
def test_unsafe_or_empty_lines_are_not_copied(text):
    assert inline_suggestion(text) == ""


@pytest.mark.parametrize("text", UNSAFE)
def test_unsafe_line_never_copies_a_different_prompt(configured, provider, clipboard, text):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    payload = {**PAYLOAD, "last_assistant_message": text}
    assert handle_stop(payload, store=configured, provider=provider, clipboard=clipboard) is None
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


def test_only_the_end_of_the_reply_counts():
    text = "Next prompt: Add a regression test for logout.\n" + "\n".join(["more"] * 5)
    assert inline_suggestion(text) is None


def test_inline_stop_copies_exactly_the_line(configured, clipboard, notifications):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    provider = Mock()
    last = reply("下一步建议：给登出流程加一个回归测试。")
    payload = {**PAYLOAD, "last_assistant_message": last}
    text = handle_stop(payload, store=configured, provider=provider, clipboard=clipboard)
    provider.generate.assert_not_called()
    clipboard.copy.assert_called_once_with("给登出流程加一个回归测试。")
    # The reply already shows the prompt, so only the copy status is added.
    assert text == "✓ 已复制到剪贴板"
    notifications.assert_called_once_with("下一句已复制", "给登出流程加一个回归测试。")


def test_inline_display_only_adds_nothing(configured, clipboard):
    payload = {**PAYLOAD, "last_assistant_message": reply("Next prompt: Add a logout test.")}
    assert handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard) is None
    clipboard.copy.assert_not_called()


def test_inline_falls_back_to_the_model_without_a_line(configured, provider, clipboard):
    payload = {**PAYLOAD, "last_assistant_message": "Fixed it."}
    text = handle_stop(
        payload,
        store=configured,
        conversation=Mock(read=Mock(return_value=[Message("user", "Fix the login redirect.")])),
        provider=provider,
        clipboard=clipboard,
    )
    provider.generate.assert_called_once()
    assert text == "Next prompt:\nRun the full regression suite and review the final diff."


def run_context(tmp_path, payload):
    return subprocess.run(
        [sys.executable, str(ROOT / "hooks/context.py")],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )


def test_context_entrypoint_prints_plain_text_by_default(tmp_path):
    start = run_context(tmp_path, START)
    assert start.returncode == 0
    # Plain text (not JSON) so Codex records it as developer context.
    assert start.stdout.decode("utf-8").startswith("NextPrompt is installed.")
    prompt = run_context(tmp_path, PROMPT)
    assert prompt.returncode == 0
    assert prompt.stdout.decode("utf-8").strip() == INLINE_REMINDER


def test_context_entrypoint_silent_in_model_mode(tmp_path):
    ConfigStore(tmp_path).update(lambda cfg: cfg.update(source="model"))
    result = run_context(tmp_path, START)
    assert result.returncode == 0 and result.stdout == b""


def test_shipped_hooks_cover_all_three_events():
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert list(hooks) == ["SessionStart", "UserPromptSubmit", "Stop"]
    for event in ("SessionStart", "UserPromptSubmit"):
        assert "context.py" in hooks[event][0]["hooks"][0]["command"]
