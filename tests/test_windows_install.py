"""Exercise the real installer with fake prerequisite/CLI commands; never download."""

import json
import os
import shutil
import subprocess
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
        $global:calls.Add(@{ command = 'doctor'; arguments = @($args) })
        $global:LASTEXITCODE = [int]$global:case.doctor_exit
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
try {
    & $env:NEXTPROMPT_INSTALL_TEST_SCRIPT -Probe
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
        ([] if python == "existing" else ["winget"]) + ["codex", "codex", "doctor"]
    )
    if python != "existing":
        args = calls[0]["arguments"]
        assert args[args.index("--id") + 1] == "Python.Python.3.12"
        assert args[args.index("--scope") + 1] == "user"
        assert args[args.index("--source") + 1] == "winget"
        assert "--silent" in args and "--disable-interactivity" in args
    assert "--probe" in calls[-1]["arguments"]
    output = result["output"]
    assert "No setup is required to display suggestions" in output
    assert "Fully quit and reopen Codex" in output
    assert "Open /hooks" in output and "approve/trust it" in output
    assert "Existing settings are preserved" in output
    assert "Optional: run $nextprompt-setup" in output


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
    assert not run_installer(doctor_exit=1)["success"]


def run_installer(**overrides):
    case = {"python": "existing", "winget": "available", "winget_exit": 0, "doctor_exit": 0}
    case.update(overrides)
    env = {
        **os.environ,
        "NEXTPROMPT_INSTALL_TEST_CASE": json.dumps(case),
        "NEXTPROMPT_INSTALL_TEST_SCRIPT": str(ROOT / "scripts/install.ps1"),
    }
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
    return parsed
