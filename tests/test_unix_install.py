"""Exercise scripts/install.sh with a fake Codex CLI and doctor; never touches real Codex."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SH = shutil.which("sh")
pytestmark = pytest.mark.skipif(os.name == "nt" or not SH, reason="POSIX sh only")

FAKE_CODEX = """#!/bin/sh
echo "codex $*" >> "$NEXTPROMPT_TEST_LOG"
exit "${FAKE_CODEX_EXIT:-0}"
"""

# Runs the real interpreter, except doctor.py, whose result the test chooses.
FAKE_PYTHON = """#!/bin/sh
case "$1" in
    *doctor.py) echo "doctor $*" >> "$NEXTPROMPT_TEST_LOG"; exit "${FAKE_DOCTOR_EXIT:-0}" ;;
    *nextprompt.py) echo "setup $*" >> "$NEXTPROMPT_TEST_LOG" ;;
esac
exec "$NEXTPROMPT_TEST_PYTHON" "$@"
"""


# Shadows any real interpreter: too old for NextPrompt.
OLD_PYTHON = """#!/bin/sh
exit 1
"""

# A package manager that "installs" Python by putting the working shim in place.
FAKE_INSTALLER = """#!/bin/sh
echo "$(basename "$0") $*" >> "$NEXTPROMPT_TEST_LOG"
case "$*" in *update*) exit 0 ;; esac
cp "$FAKE_PYTHON_SOURCE" "$(dirname "$0")/python3"
"""


def run_installer(*args, codex_exit=0, doctor_exit=0, extra=None, answers=None):
    """Run install.sh; with `answers`, stdin is a terminal that already holds those lines."""
    with tempfile.TemporaryDirectory(prefix="nextprompt-install-test-") as tmp:
        bin_dir = Path(tmp) / "bin"
        bin_dir.mkdir()
        source = Path(tmp) / "python-shim"
        source.write_text(FAKE_PYTHON)
        source.chmod(0o755)
        files = {"codex": FAKE_CODEX, "python3": FAKE_PYTHON, **(extra or {})}
        for name, body in files.items():
            path = bin_dir / name
            path.write_text(body)
            path.chmod(0o755)
        log = Path(tmp) / "calls.log"
        log.touch()
        data = Path(tmp) / "data"
        env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "PLUGIN_DATA": str(data),
            "NEXTPROMPT_TEST_LOG": str(log),
            "NEXTPROMPT_TEST_PYTHON": sys.executable,
            "FAKE_CODEX_EXIT": str(codex_exit),
            "FAKE_DOCTOR_EXIT": str(doctor_exit),
            "FAKE_PYTHON_SOURCE": str(source),
        }
        stdin, tty = subprocess.DEVNULL, None
        if answers is not None:
            # The installer only asks when stdin is a terminal.
            master, tty = os.openpty()
            os.write(master, "".join(answer + "\n" for answer in answers).encode())
            stdin = tty
        try:
            result = subprocess.run(
                [SH, str(ROOT / "scripts/install.sh"), *args],
                env=env,
                stdin=stdin,
                capture_output=True,
                timeout=30,
            )
        finally:
            if tty is not None:
                os.close(tty)
                os.close(master)
        config_path = data / "config.json"
        return {
            "code": result.returncode,
            "output": result.stdout.decode("utf-8") + result.stderr.decode("utf-8"),
            "calls": [line.split()[0] for line in log.read_text().splitlines()],
            "log": log.read_text(),
            "config": json.loads(config_path.read_text()) if config_path.exists() else None,
        }


@pytest.mark.parametrize("auto_copy", ["on", "off"])
def test_install_saves_choice_and_prints_usage(auto_copy):
    result = run_installer("--auto-copy", auto_copy)
    assert result["code"] == 0, result["output"]
    assert result["calls"] == ["codex", "codex", "doctor", "setup"]
    assert f"codex plugin marketplace add {ROOT}" in result["log"]
    assert "codex plugin add nextprompt@nextprompt" in result["log"]
    assert result["config"]["clipboard"]["auto_copy"] is (auto_copy == "on")
    assert result["config"]["notify"] is True
    output = result["output"]
    assert "NextPrompt installed successfully" in output
    assert "Desktop notifications: ON." in output
    assert "Recommended settings" not in output
    assert ("Automatic clipboard copy: ON" in output) is (auto_copy == "on")
    assert ("Automatic clipboard copy: OFF" in output) is (auto_copy == "off")
    assert "Fully quit and reopen Codex" in output
    assert "UserPromptSubmit and Stop hooks, and trust them" in output
    assert "Next prompt:" in output
    assert "never sent automatically" in output
    assert "$nextprompt-setup" in output


def test_probe_is_passed_to_doctor():
    result = run_installer("--auto-copy=on", "--probe")
    assert result["code"] == 0, result["output"]
    assert "--probe" in result["log"]


def test_non_interactive_without_choice_saves_nothing():
    result = run_installer()
    assert result["code"] != 0
    assert "pass --auto-copy on|off" in result["output"]
    assert "installed successfully" not in result["output"]
    assert result["config"] is None


@pytest.mark.parametrize("overrides", [{"codex_exit": 1}, {"doctor_exit": 1}])
def test_failure_never_reports_success(overrides):
    result = run_installer("--auto-copy", "on", **overrides)
    assert result["code"] != 0
    assert "setup" not in result["calls"]
    assert "installed successfully" not in result["output"]
    assert result["config"] is None


@pytest.mark.parametrize("args", [("--auto-copy", "maybe"), ("--notify", "maybe")])
def test_invalid_option_is_rejected_before_installing(args):
    result = run_installer(*args)
    assert result["code"] != 0
    assert result["calls"] == []


@pytest.mark.parametrize(
    ("args", "auto_copy", "notify"),
    [(("--notify", "off"), True, False), (("--auto-copy=off", "--notify=on"), False, True)],
)
def test_notify_flag_is_saved_without_prompting(args, auto_copy, notify):
    result = run_installer(*args)
    assert result["code"] == 0, result["output"]
    assert result["config"]["clipboard"]["auto_copy"] is auto_copy
    assert result["config"]["notify"] is notify
    assert ("Desktop notifications: OFF." in result["output"]) is not notify
    assert "Recommended settings" not in result["output"]


@pytest.mark.parametrize(
    ("answers", "auto_copy", "notify"),
    [
        ([""], True, True),
        (["Y"], True, True),
        (["n", "yn"], True, False),
        (["no", "ny"], False, True),
        (["n", "nn"], False, False),
        (["n", "yy"], True, True),
        (["YN"], True, False),
        (["maybe", "n", "x", "nn"], False, False),
    ],
)
def test_recommended_settings_prompt(answers, auto_copy, notify):
    result = run_installer(answers=answers)
    assert result["code"] == 0, result["output"]
    assert result["config"]["clipboard"]["auto_copy"] is auto_copy
    assert result["config"]["notify"] is notify
    output = result["output"]
    assert "Recommended settings" in output and "(recommended)" in output
    assert ("Automatic clipboard copy: ON." in output) is auto_copy
    assert ("Desktop notifications: ON." in output) is notify


def test_macos_without_python_installs_it_with_homebrew():
    result = run_installer(
        "--auto-copy",
        "on",
        extra={
            "python3": OLD_PYTHON,
            "python": OLD_PYTHON,
            "uname": "#!/bin/sh\necho Darwin\n",
            "brew": FAKE_INSTALLER,
        },
    )
    assert result["code"] == 0, result["output"]
    assert "brew install python3" in result["log"]
    assert result["calls"][:3] == ["brew", "codex", "codex"]
    assert "NextPrompt installed successfully" in result["output"]


def test_linux_without_python_installs_it_with_the_package_manager():
    result = run_installer(
        "--auto-copy",
        "off",
        extra={
            "python3": OLD_PYTHON,
            "python": OLD_PYTHON,
            "uname": "#!/bin/sh\necho Linux\n",
            "id": "#!/bin/sh\necho 0\n",
            "apt-get": FAKE_INSTALLER,
        },
    )
    assert result["code"] == 0, result["output"]
    assert "apt-get install -y python3" in result["log"]
    assert result["config"]["clipboard"]["auto_copy"] is False
