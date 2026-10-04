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
    handle_session_start,
    handle_stop,
    handle_user_prompt_submit,
    inline_suggestion,
)
from nextprompt.transcript import Message

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = {"hook_event_name": "Stop", "transcript_path": "/fake/session", "stop_hook_active": False}

START = {"hook_event_name": "SessionStart", "source": "startup", "session_id": "s"}
SUBMIT = {"hook_event_name": "UserPromptSubmit", "prompt": "Fix the logout redirect."}


@pytest.fixture
def inline(configured):
    configured.update(lambda cfg: cfg.update(source="inline"))
    return configured


def reply(last_line):
    return f"Fixed the redirect and the targeted tests pass.\n\n{last_line}"


def test_source_defaults_to_inline_and_validates(tmp_path):
    store = ConfigStore(tmp_path)
    assert store.load()["source"] == "inline"
    with pytest.raises(ConfigError):
        store.update(lambda cfg: cfg.update(source="root"))


def test_session_start_injects_only_in_inline_mode(configured, inline):
    text = handle_session_start(START, store=inline)
    assert text == INLINE_PATH.read_text(encoding="utf-8").strip()
    assert "Next prompt:" in text and "下一步：" in text
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
        "- **Next prompt**: `Add a regression test for the logout redirect.`",
        "Next prompt:\nAdd a regression test for the logout redirect.",
    ],
)
def test_extracts_the_marked_line(settings, line):
    expected = "Add a regression test for the logout redirect."
    assert inline_suggestion(reply(line), settings) == expected


@pytest.mark.parametrize(
    "line",
    [
        "下一步：给登出流程加一个回归测试。",
        "**下一步：** 给登出流程加一个回归测试。",
        "下一步建议: 给登出流程加一个回归测试。",
    ],
)
def test_extracts_the_chinese_label(settings, line):
    assert inline_suggestion(reply(line), settings) == "给登出流程加一个回归测试。"


@pytest.mark.parametrize(
    "line",
    [
        "Next prompt: continue",
        # Two sentences and over the 20-word model limit, but this is what the reply shows.
        "Next prompt: Add the logout test. Then compare it with the login flow, the session "
        "expiry flow and the password reset flow end to end.",
    ],
)
def test_copies_the_visible_line_verbatim(settings, line):
    assert inline_suggestion(reply(line), settings) == line.removeprefix("Next prompt: ")


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "All done, nothing else to do.",
        "Next prompt: sk-abcdefghijklmnopqrstuvwxyz0123456789 rotate this key",
        "Next prompt: **",
    ],
)
def test_rejects_missing_empty_or_secret_lines(settings, text):
    assert inline_suggestion(text, settings) is None


def test_a_bare_label_heading_above_a_list_is_not_a_prompt(settings):
    text = "改好了。\n下一步：\n- 跑测试\n- 合并"
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


def test_chinese_label_line_is_copied_exactly(inline, clipboard):
    inline.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    payload = {**PAYLOAD, "last_assistant_message": reply("下一步：继续 review 这个 PR 的剩余评论")}
    text = handle_stop(payload, store=inline, provider=Mock(), clipboard=clipboard)
    clipboard.copy.assert_called_once_with("继续 review 这个 PR 的剩余评论")
    assert text == "✓ 已复制到剪贴板"


def test_unsafe_visible_line_copies_nothing_rather_than_a_different_prompt(
    inline, provider, clipboard
):
    inline.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    secret = "Next prompt: rotate sk-abcdefghijklmnopqrstuvwxyz0123456789 now"
    payload = {**PAYLOAD, "last_assistant_message": reply(secret)}
    assert handle_stop(payload, store=inline, provider=provider, clipboard=clipboard) is None
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


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


def test_session_start_entrypoint_silent_in_model_mode(tmp_path):
    ConfigStore(tmp_path).update(lambda cfg: cfg.update(source="model"))
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks/session_start.py")],
        input=json.dumps(START).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )
    assert result.returncode == 0 and result.stdout == b""


def test_session_start_entrypoint_injects_by_default(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks/session_start.py")],
        input=json.dumps(START).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )
    assert result.returncode == 0
    assert result.stdout.decode("utf-8").startswith("NextPrompt is installed.")


@pytest.mark.parametrize(
    ("prompt", "label"),
    [("Fix the logout redirect.", "Next prompt:"), ("修一下登出跳转", "下一步：")],
)
def test_prompt_submit_reminds_with_the_users_label(inline, prompt, label):
    text = handle_user_prompt_submit({**SUBMIT, "prompt": prompt}, store=inline)
    assert f"exact last line: {label} <" in text


def test_prompt_submit_follows_the_configured_language(inline):
    inline.update(lambda cfg: cfg.update(language="zh"))
    assert "下一步：" in handle_user_prompt_submit(SUBMIT, store=inline)


@pytest.mark.parametrize(
    "change",
    [
        lambda cfg: cfg.update(source="model"),
        lambda cfg: cfg.update(enabled=False),
        lambda cfg: cfg.update(trigger_mode="manual"),
    ],
)
def test_prompt_submit_silent_outside_inline_mode(inline, change):
    inline.update(change)
    assert handle_user_prompt_submit(SUBMIT, store=inline) is None


def test_prompt_submit_ignores_internal_runs_and_other_events(inline, monkeypatch):
    assert handle_user_prompt_submit({**SUBMIT, "hook_event_name": "Stop"}, store=inline) is None
    assert handle_user_prompt_submit("not a payload", store=inline) is None
    monkeypatch.setenv("NEXTPROMPT_INTERNAL", "1")
    assert handle_user_prompt_submit(SUBMIT, store=inline) is None


def test_prompt_submit_entrypoint_emits_context_only(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks/user_prompt_submit.py")],
        input=json.dumps({**SUBMIT, "prompt": "修一下登出跳转"}).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    # Never a decision, reason or continue flag that could block or redirect the turn.
    assert set(output) == {"hookSpecificOutput"}
    assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "下一步：" in output["hookSpecificOutput"]["additionalContext"]


def test_prompt_submit_entrypoint_silent_in_model_mode(tmp_path):
    ConfigStore(tmp_path).update(lambda cfg: cfg.update(source="model"))
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks/user_prompt_submit.py")],
        input=json.dumps(SUBMIT).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )
    assert result.returncode == 0 and result.stdout == b""
