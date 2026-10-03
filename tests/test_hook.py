import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from nextprompt.config import ConfigStore
from nextprompt.hook import SETUP_NOTICE, handle_stop
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


def test_first_run_once_no_inference(tmp_path, provider, clipboard):
    store = ConfigStore(tmp_path)
    adapter = conversation()
    assert (
        handle_stop(
            PAYLOAD, store=store, conversation=adapter, provider=provider, clipboard=clipboard
        )
        == SETUP_NOTICE
    )
    assert handle_stop(PAYLOAD, store=store) is None
    assert store.load()["clipboard"]["auto_copy"] is None
    adapter.read.assert_not_called()
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


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


@pytest.mark.parametrize("input_bytes", [b"", b"bad JSON", b"[]", b"x" * 70000])
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
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks/stop.py")],
        input=json.dumps(PAYLOAD).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path), "PYTHONIOENCODING": "ascii"},
        timeout=3,
    )
    assert result.returncode == 0 and result.stderr == b""
    assert json.loads(result.stdout)["systemMessage"] == SETUP_NOTICE
