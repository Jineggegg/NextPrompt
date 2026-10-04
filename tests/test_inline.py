import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from nextprompt.config import ConfigError, ConfigStore
from nextprompt.hook import INLINE_PATH, handle_session_start, handle_stop, inline_suggestion
from nextprompt.transcript import Message

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = {"hook_event_name": "Stop", "transcript_path": "/fake/session", "stop_hook_active": False}

START = {"hook_event_name": "SessionStart", "source": "startup", "session_id": "s"}


@pytest.fixture
def inline(configured):
    configured.update(lambda cfg: cfg.update(source="inline"))
    return configured


def reply(last_line):
    return f"Fixed the redirect and the targeted tests pass.\n\n{last_line}"


def test_source_defaults_to_model_and_validates(tmp_path):
    store = ConfigStore(tmp_path)
    assert store.load()["source"] == "model"
    with pytest.raises(ConfigError):
        store.update(lambda cfg: cfg.update(source="root"))


def test_session_start_injects_only_in_inline_mode(configured, inline):
    text = handle_session_start(START, store=inline)
    assert text == INLINE_PATH.read_text(encoding="utf-8").strip()
    assert "Next prompt:" in text
    inline.update(lambda cfg: cfg.update(source="model"))
    assert handle_session_start(START, store=inline) is None


@pytest.mark.parametrize(
    "change",
    [lambda cfg: cfg.update(enabled=False), lambda cfg: cfg.update(trigger_mode="manual")],
)
def test_session_start_silent_when_off(inline, change):
    inline.update(change)
    assert handle_session_start(START, store=inline) is None


def test_session_start_ignores_internal_runs_and_other_events(inline, monkeypatch):
    assert handle_session_start({**START, "hook_event_name": "Stop"}, store=inline) is None
    monkeypatch.setenv("NEXTPROMPT_INTERNAL", "1")
    assert handle_session_start(START, store=inline) is None


@pytest.mark.parametrize(
    "line",
    [
        "Next prompt: Add a regression test for the logout redirect.",
        "**Next prompt:** Add a regression test for the logout redirect.",
        "> Next prompt：Add a regression test for the logout redirect.",
    ],
)
def test_extracts_the_marked_line(settings, line):
    expected = "Add a regression test for the logout redirect."
    assert inline_suggestion(reply(line), settings) == expected


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "All done, nothing else to do.",
        "Next prompt: continue",
        "Next prompt: Run the full regression suite now.",  # just completed below
        "Next prompt: sk-abcdefghijklmnopqrstuvwxyz0123456789 rotate this key",
    ],
)
def test_rejects_missing_generic_repeated_or_secret_lines(settings, text):
    if text and "regression" in text:
        text = "The full regression suite passed.\n" + text
    assert inline_suggestion(text, settings) is None


def test_only_the_end_of_the_reply_counts(settings):
    text = "Next prompt: Add a regression test for logout.\n" + "\n".join(["more"] * 5)
    assert inline_suggestion(text, settings) is None


def test_inline_stop_copies_without_a_model_call(inline, clipboard, notifications):
    inline.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    provider = Mock()
    payload = {
        **PAYLOAD,
        "last_assistant_message": reply("Next prompt: 给登出流程加一个回归测试。"),
    }
    text = handle_stop(payload, store=inline, provider=provider, clipboard=clipboard)
    provider.generate.assert_not_called()
    clipboard.copy.assert_called_once_with("给登出流程加一个回归测试。")
    # The reply already shows the prompt, so only the copy status is added.
    assert text == "✓ 已复制到剪贴板"
    notifications.assert_called_once_with("下一句已复制", "给登出流程加一个回归测试。")


def test_inline_display_only_adds_nothing(inline, clipboard):
    payload = {**PAYLOAD, "last_assistant_message": reply("Next prompt: Add a logout test.")}
    assert handle_stop(payload, store=inline, provider=Mock(), clipboard=clipboard) is None
    clipboard.copy.assert_not_called()


def test_inline_falls_back_to_the_model_without_a_line(inline, provider, clipboard):
    payload = {**PAYLOAD, "last_assistant_message": "Fixed it."}
    text = handle_stop(
        payload,
        store=inline,
        conversation=Mock(read=Mock(return_value=[Message("user", "Fix the login redirect.")])),
        provider=provider,
        clipboard=clipboard,
    )
    provider.generate.assert_called_once()
    assert text == "Next prompt:\nRun the full regression suite and review the final diff."


def test_session_start_entrypoint_prints_plain_context(tmp_path):
    ConfigStore(tmp_path).update(lambda cfg: cfg.update(source="inline"))
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks/session_start.py")],
        input=json.dumps(START).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )
    assert result.returncode == 0
    # Plain text (not JSON) so Codex records it as developer context.
    assert result.stdout.decode("utf-8").startswith("NextPrompt is installed.")


def test_session_start_entrypoint_silent_by_default(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks/session_start.py")],
        input=json.dumps(START).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )
    assert result.returncode == 0 and result.stdout == b""
