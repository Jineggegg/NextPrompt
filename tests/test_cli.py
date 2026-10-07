import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from nextprompt.cli import hook_interpreter, main
from nextprompt.config import ConfigStore
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


@pytest.mark.parametrize("legacy_unset", [False, True])
def test_manual_suggest_without_setup(tmp_path, capsys, monkeypatch, legacy_unset):
    store = ConfigStore(tmp_path)
    if legacy_unset:
        store.update(lambda cfg: cfg["clipboard"].update(auto_copy=None))
    stdin = Mock(buffer=io.BytesIO(b'{"messages":[{"role":"user","text":"Test the fix."}]}'))
    monkeypatch.setattr("nextprompt.cli.sys.stdin", stdin)
    generate = Mock(return_value="Next prompt:\nRun the full regression suite.")
    monkeypatch.setattr("nextprompt.cli.generate_suggestion", generate)
    assert main(["--data-dir", str(tmp_path), "suggest", "--context-stdin"]) == 0
    assert "Next prompt:" in capsys.readouterr().out
    assert generate.call_args.args[1]["clipboard"]["auto_copy"] is (None if legacy_unset else True)
    assert store.path.exists() is legacy_unset


@pytest.mark.parametrize("existing_copy", [False, True])
def test_non_clipboard_setup_preserves_choice(tmp_path, capsys, existing_copy):
    store = ConfigStore(tmp_path)
    store.update(lambda cfg: cfg["clipboard"].update(auto_copy=existing_copy))
    assert main(["--data-dir", str(tmp_path), "setup", "--max-words", "15"]) == 0
    assert store.load()["clipboard"]["auto_copy"] is existing_copy
    assert "Choose 1 or 2" not in capsys.readouterr().out


def test_invalid_limits_do_not_corrupt_config(tmp_path, capsys):
    args = ["--data-dir", str(tmp_path)]
    assert main([*args, "setup", "--auto-copy", "off"]) == 0
    before = (tmp_path / "config.json").read_bytes()
    assert main([*args, "setup", "--context-messages", "20"]) == 1
    assert before == (tmp_path / "config.json").read_bytes()
    assert "configuration error: setting exceeds V1 limits" in capsys.readouterr().out


def test_doctor_reports_invalid_config_and_continues(tmp_path, capsys, doctor_provider):
    (tmp_path / "config.json").write_text("{bad")
    assert main(["--data-dir", str(tmp_path), "doctor"]) == 1
    output = capsys.readouterr().out
    assert "Config              ✗ invalid config" in output
    assert "Repair or delete" in output
    assert "Hook self-test      ✓" in output  # Remaining checks still run.
    assert "Check configuration with nextprompt doctor" not in output


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
    monkeypatch.setattr("nextprompt.cli.hook_interpreter", lambda: ("python3", "3.9.6"))
    monkeypatch.setattr("nextprompt.cli.check_hooks", lambda root: True)
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


def test_doctor_accepts_a_valid_silent_response(tmp_path, capsys, doctor_provider):
    doctor_provider.generate.return_value = ""
    assert main(["--data-dir", str(tmp_path), "doctor", "--probe"]) == 0
    assert "✓ valid response (no suggestion needed)" in capsys.readouterr().out
    assert doctor_provider.generate.call_count == 1


def test_doctor_without_probe_does_not_run_inference(tmp_path, capsys, doctor_provider):
    assert main(["--data-dir", str(tmp_path), "doctor"]) == 0
    output = capsys.readouterr().out
    assert "no separate CLI login or model request needed" in output
    doctor_provider.check_cli.assert_not_called()
    doctor_provider.discover_models.assert_not_called()
    assert "defaults ready (auto-copy on)" in output
    assert "setup pending" not in output
    doctor_provider.generate.assert_not_called()


def test_doctor_missing_auth_returns_nonzero(tmp_path, capsys, doctor_provider, monkeypatch):
    ConfigStore(tmp_path).update(lambda cfg: cfg.update(source="model"))
    monkeypatch.setattr(
        "nextprompt.cli.run_process",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, b"", b"Not logged in"),
    )
    assert main(["--data-dir", str(tmp_path), "doctor"]) == 1
    assert "Authentication      ✗" in capsys.readouterr().out


def test_language_setting(tmp_path, capsys):
    args = ["--data-dir", str(tmp_path)]
    assert main([*args, "status"]) == 0
    assert "Language:         auto (follows your messages)" in capsys.readouterr().out
    assert main([*args, "setup", "--language", "zh-TW"]) == 0
    store = ConfigStore(tmp_path)
    assert store.load()["language"] == "zh-TW"
    assert store.load()["clipboard"]["auto_copy"] is True  # Default kept; not a clipboard choice.
    assert "Language:         zh-TW" in capsys.readouterr().out


def test_doctor_fails_when_hook_has_no_python(tmp_path, capsys, doctor_provider, monkeypatch):
    monkeypatch.setattr("nextprompt.cli.hook_interpreter", lambda: None)
    assert main(["--data-dir", str(tmp_path), "doctor"]) == 1
    assert "Hook Python         ✗" in capsys.readouterr().out


def test_hook_interpreter_falls_back_to_python3(monkeypatch):
    monkeypatch.setattr(
        "nextprompt.cli.shutil.which", lambda name: None if name == "python" else sys.executable
    )
    name, version = hook_interpreter()
    assert name == "python3" and version.startswith(f"{sys.version_info[0]}.")


def test_hook_interpreter_falls_back_to_py_launcher(monkeypatch):
    monkeypatch.setattr(
        "nextprompt.cli.shutil.which", lambda name: sys.executable if name == "py" else None
    )
    calls = []
    monkeypatch.setattr(
        "nextprompt.cli.run_process",
        lambda args, **k: (
            calls.append(args) or subprocess.CompletedProcess(args, 0, b"3.12.10\n", b"")
        ),
    )
    assert hook_interpreter() == ("py -3", "3.12.10")
    assert calls[0][1] == "-3"


def test_hook_interpreter_skips_an_old_python3_for_a_versioned_one(monkeypatch):
    monkeypatch.setattr(
        "nextprompt.cli.shutil.which",
        lambda name: f"/usr/bin/{name}" if name in ("python3", "python3.11") else None,
    )
    monkeypatch.setattr(
        "nextprompt.cli.run_process",
        lambda args, **k: subprocess.CompletedProcess(
            args, 0, b"3.8.10\n" if args[0].endswith("python3") else b"3.11.2\n", b""
        ),
    )
    assert hook_interpreter() == ("python3.11", "3.11.2")


def test_hook_interpreter_rejects_old_python(monkeypatch):
    monkeypatch.setattr("nextprompt.cli.shutil.which", lambda name: "python-old")
    monkeypatch.setattr(
        "nextprompt.cli.run_process",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, b"3.8.18\n", b""),
    )
    assert hook_interpreter() is None


def test_doctor_fails_on_real_launcher_failure(tmp_path, capsys, doctor_provider, monkeypatch):
    monkeypatch.setattr("nextprompt.cli.check_hooks", lambda root: False)
    assert main(["--data-dir", str(tmp_path), "doctor"]) == 1
    assert "Hook self-test      ✗" in capsys.readouterr().out
