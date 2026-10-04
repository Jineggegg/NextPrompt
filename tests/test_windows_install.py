"""Exercise the real installer with fake prerequisite/CLI commands; never download."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which("pwsh") or shutil.which("powershell")
pytestmark = pytest.mark.skipif(os.name != "nt" or not SHELL, reason="Windows PowerShell only")

HARNESS = r"""
$global:case = $env:NEXTPROMPT_INSTALL_TEST_CASE | ConvertFrom-Json
$global:installed = $false
$global:calls = [System.Collections.Generic.List[object]]::new()
$global:LASTEXITCODE = 0
function Get-Command {
    param($Name, $ErrorAction)
    switch ($Name) {
        'python' {
            if ($global:case.python -eq 'missing' -and -not $global:installed) { return $null }
            if ($global:case.python -eq 'still-missing') { return $null }
            return [PSCustomObject]@{ Source = 'Fake-Python' }
        }
        'winget' {
            if ($global:case.winget -eq 'missing') { return $null }
            return [PSCustomObject]@{ Source = 'Fake-Winget' }
        }
        'codex' { return [PSCustomObject]@{ Source = 'Fake-Codex' } }
        default { throw 'Unexpected command lookup in installer' }
    }
}
function Fake-Python {
    if ($args[0] -eq '-c') {
        if ($global:case.python -eq 'alias' -and -not $global:installed) {
            throw 'Alias unavailable'
        }
        $global:LASTEXITCODE = 0
        if ($global:case.python -eq 'old' -and -not $global:installed) { '3.9.13' }
        else { '3.12.10' }
    } else {
        if ($args[1] -eq 'setup') {
            $global:calls.Add(@{ command = 'setup'; arguments = @($args) })
            if ($global:case.setup_exit -ne 0) {
                $global:LASTEXITCODE = [int]$global:case.setup_exit
            } else {
                $setupArgs = @($args[0], '--data-dir', $env:NEXTPROMPT_TEST_DATA,
                    'setup', '--auto-copy', $args[-1])
                & $env:NEXTPROMPT_TEST_PYTHON @setupArgs
            }
        } else {
            $global:calls.Add(@{ command = 'doctor'; arguments = @($args) })
            $global:LASTEXITCODE = [int]$global:case.doctor_exit
        }
    }
}
function Fake-Winget {
    $global:calls.Add(@{ command = 'winget'; arguments = @($args) })
    $global:LASTEXITCODE = [int]$global:case.winget_exit
    if ($global:LASTEXITCODE -eq 0) { $global:installed = $true }
}
function Fake-Codex {
    $global:calls.Add(@{ command = 'codex'; arguments = @($args) })
    $global:LASTEXITCODE = 0
}
function Read-Host {
    param($Prompt)
    $global:calls.Add(@{ command = 'prompt'; arguments = @($Prompt) })
    if ($global:case.prompt_error) { throw 'No interactive input available' }
    $answer = $global:case.answers[0]
    $global:case.answers = @($global:case.answers | Select-Object -Skip 1)
    return $answer
}
try {
    $parameters = @{ Probe = $true }
    if ($global:case.auto_copy) { $parameters.AutoCopy = $global:case.auto_copy }
    & $env:NEXTPROMPT_INSTALL_TEST_SCRIPT @parameters
    $result = @{ success = $true; calls = @($global:calls.ToArray()) }
} catch {
    $result = @{ success = $false; calls = @($global:calls.ToArray()) }
}
$result | ConvertTo-Json -Depth 8 -Compress
"""


@pytest.mark.parametrize("python", ["existing", "missing", "old", "alias"])
def test_installer_prerequisite_paths(python):
    result = run_installer(python=python)
    assert result["success"]
    calls = result["calls"]
    assert [c["command"] for c in calls] == (
        ([] if python == "existing" else ["winget"])
        + ["codex", "codex", "doctor", "prompt", "setup"]
    )
    if python != "existing":
        args = calls[0]["arguments"]
        assert args[args.index("--id") + 1] == "Python.Python.3.12"
        assert args[args.index("--scope") + 1] == "user"
        assert args[args.index("--source") + 1] == "winget"
        assert "--silent" in args and "--disable-interactivity" in args
    assert "--probe" in next(c for c in calls if c["command"] == "doctor")["arguments"]
    output = result["output"]
    assert "NextPrompt installed successfully" in output
    assert "No additional setup is required" in output
    assert "Fully quit and reopen Codex" in output
    assert "Open /hooks" in output and "UserPromptSubmit and Stop hooks, and trust them" in output
    assert "Other existing settings are preserved" in output
    assert "Desktop notifications: ON by default" in output
    assert "turn off notifications" in output
    assert "Optional: run $nextprompt-setup" in output
    assert "Automatic clipboard copy: OFF" in output
    assert result["config"]["clipboard"]["auto_copy"] is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"python": "missing", "winget": "missing"},
        {"python": "missing", "winget_exit": 1},
        {"python": "still-missing"},
    ],
)
def test_prerequisite_failure_never_registers_plugin(overrides):
    result = run_installer(**overrides)
    assert not result["success"]
    assert all(c["command"] == "winget" for c in result["calls"])


def test_doctor_failure_is_not_reported_as_success():
    result = run_installer(doctor_exit=1)
    assert not result["success"]
    assert not any(c["command"] in ("prompt", "setup") for c in result["calls"])
    assert "installed successfully" not in result["output"]


@pytest.mark.parametrize("answer", ["y", "Y", "yes", " YES ", ""])
def test_yes_saves_consent_and_reports_automatic_copy(answer):
    result = run_installer(answers=[answer])
    assert result["success"]
    assert result["config"]["clipboard"]["auto_copy"] is True
    assert "Automatic clipboard copy: ON" in result["output"]
    assert "New suggestions will be copied automatically" in result["output"]
    assert "Automatic clipboard copy: OFF" not in result["output"]


@pytest.mark.parametrize("answer", ["n", "N", "no", " NO "])
def test_no_answer_saves_display_only(answer):
    result = run_installer(answers=[answer])
    assert result["success"]
    assert result["config"]["clipboard"]["auto_copy"] is False
    assert "Automatic clipboard copy: OFF" in result["output"]
    assert "Automatic clipboard copy: ON" not in result["output"]


def test_invalid_answer_reprompts_before_saving():
    result = run_installer(answers=["maybe", "y"])
    assert result["success"]
    assert result["config"]["clipboard"]["auto_copy"] is True
    assert sum(c["command"] == "prompt" for c in result["calls"]) == 2


@pytest.mark.parametrize("auto_copy", ["on", "off"])
def test_explicit_flag_does_not_prompt(auto_copy):
    result = run_installer(auto_copy=auto_copy)
    assert result["success"]
    assert result["config"]["clipboard"]["auto_copy"] is (auto_copy == "on")
    assert not any(c["command"] == "prompt" for c in result["calls"])


@pytest.mark.parametrize("overrides", [{"setup_exit": 1}, {"prompt_error": True}])
def test_preference_failure_never_reports_success(overrides):
    result = run_installer(**overrides)
    assert not result["success"]
    assert "installed successfully" not in result["output"]
    assert result["config"] is None


def run_installer(**overrides):
    case = {
        "python": "existing",
        "winget": "available",
        "winget_exit": 0,
        "doctor_exit": 0,
        "setup_exit": 0,
        "answers": ["n"],
        "auto_copy": None,
        "prompt_error": False,
    }
    case.update(overrides)
    env = {
        **os.environ,
        "NEXTPROMPT_INSTALL_TEST_CASE": json.dumps(case),
        "NEXTPROMPT_INSTALL_TEST_SCRIPT": str(ROOT / "scripts/install.ps1"),
    }
    with tempfile.TemporaryDirectory(prefix="nextprompt-install-test-") as data_dir:
        env.update(NEXTPROMPT_TEST_PYTHON=sys.executable, NEXTPROMPT_TEST_DATA=data_dir)
        result = subprocess.run(
            [SHELL, "-NoProfile", "-NonInteractive", "-Command", HARNESS],
            env=env,
            capture_output=True,
            timeout=15,
            check=True,
        )
        output = result.stdout.decode("utf-8-sig").strip()
        parsed = json.loads(output.splitlines()[-1])
        parsed["output"] = output
        config_path = Path(data_dir) / "config.json"
        parsed["config"] = json.loads(config_path.read_text()) if config_path.exists() else None
        return parsed
