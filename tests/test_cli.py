import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from nextprompt.cli import main
from nextprompt.providers import ProviderUnavailable

ROOT = Path(__file__).resolve().parents[1]


def test_cli_explicit_setup_and_enable_disable(tmp_path, capsys):
    args = ["--data-dir", str(tmp_path)]
    assert main([*args, "setup", "--auto-copy", "off"]) == 0
    assert json.loads((tmp_path / "config.json").read_text())["clipboard"]["auto_copy"] is False
    assert main([*args, "disable"]) == 0
    assert main([*args, "status"]) == 0
    assert "Enabled:          No" in capsys.readouterr().out
    assert main([*args, "enable"]) == 0
    assert main([*args, "setup", "--auto-copy", "on"]) == 0
    assert json.loads((tmp_path / "config.json").read_text())["clipboard"]["auto_copy"] is True


def test_unattended_setup_never_consents(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/nextprompt.py"), "--data-dir", str(tmp_path), "setup"],
        input=b"",
        capture_output=True,
        env=os.environ,
        timeout=3,
    )
    assert result.returncode == 2
    assert not (tmp_path / "config.json").exists()


def test_invalid_limits_do_not_corrupt_config(tmp_path, capsys):
    args = ["--data-dir", str(tmp_path)]
    assert main([*args, "setup", "--auto-copy", "off"]) == 0
    before = (tmp_path / "config.json").read_bytes()
    assert main([*args, "setup", "--context-messages", "20"]) == 1
    assert before == (tmp_path / "config.json").read_bytes()


@pytest.fixture
def doctor_provider(monkeypatch):
    provider = Mock(
        check_cli=Mock(return_value="codex-cli 0.159.0-alpha.3"),
        executable=Mock(return_value="codex"),
        discover_models=Mock(
            return_value=[
                {
                    "model": "gpt-5.6-luna",
                    "supportedReasoningEfforts": [{"reasoningEffort": "low"}],
                }
            ]
        ),
        generate=Mock(return_value="Run the full regression suite and review the final diff."),
    )
    monkeypatch.setattr("nextprompt.cli.CodexSuggestionProvider", lambda *a: provider)
    monkeypatch.setattr(
        "nextprompt.cli.run_process",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, b"", b"Logged in using ChatGPT"),
    )
    monkeypatch.setattr(
        "nextprompt.cli.SystemClipboardAdapter",
        lambda **k: Mock(available=lambda: False, backend_name=lambda: "unavailable"),
    )
    return provider


@pytest.mark.parametrize("category", ["authentication", "quota", "timeout", "model"])
def test_doctor_probe_failure_returns_nonzero(tmp_path, capsys, doctor_provider, category):
    doctor_provider.generate.side_effect = ProviderUnavailable(category)
    assert main(["--data-dir", str(tmp_path), "doctor", "--probe"]) == 1
    output = capsys.readouterr().out
    assert "Inference probe     ✗" in output
    assert "token validity unverified" in output
    if category == "authentication":
        assert "Run codex login" in output
    assert not tmp_path.joinpath("config.json").exists()


def test_doctor_invalid_suggestion_fails(tmp_path, capsys, doctor_provider):
    doctor_provider.generate.return_value = "Continue."
    assert main(["--data-dir", str(tmp_path), "doctor", "--probe"]) == 1
    assert "✗ invalid response" in capsys.readouterr().out


def test_doctor_probe_succeeds_without_clipboard(tmp_path, capsys, doctor_provider):
    assert main(["--data-dir", str(tmp_path), "doctor", "--probe"]) == 0
    assert "✓ one short suggestion" in capsys.readouterr().out
    assert doctor_provider.generate.call_count == 1


def test_doctor_without_probe_does_not_run_inference(tmp_path, capsys, doctor_provider):
    assert main(["--data-dir", str(tmp_path), "doctor"]) == 0
    assert "(catalog)" in capsys.readouterr().out
    doctor_provider.generate.assert_not_called()


def test_doctor_missing_auth_returns_nonzero(tmp_path, capsys, doctor_provider, monkeypatch):
    monkeypatch.setattr(
        "nextprompt.cli.run_process",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, b"", b"Not logged in"),
    )
    assert main(["--data-dir", str(tmp_path), "doctor"]) == 1
    assert "Authentication      ✗" in capsys.readouterr().out
