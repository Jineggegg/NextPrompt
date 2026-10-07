import json
import subprocess
from pathlib import Path

from nextprompt.diagnostics import check_hooks

ROOT = Path(__file__).resolve().parents[1]


def test_real_hook_self_test_leaves_user_data_untouched(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path))
    before = list(tmp_path.iterdir())
    assert check_hooks(ROOT)
    assert list(tmp_path.iterdir()) == before


def test_silent_success_from_broken_launcher_is_a_failure(monkeypatch):
    monkeypatch.setattr(
        "nextprompt.diagnostics.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, b"", b""),
    )
    assert not check_hooks(ROOT)


def test_stop_that_never_executes_is_a_failure(monkeypatch):
    run = subprocess.run

    def skip_stop(*args, **kwargs):
        if json.loads(kwargs["input"])["hook_event_name"] == "Stop":
            return subprocess.CompletedProcess(args, 0, b"", b"")
        return run(*args, **kwargs)

    monkeypatch.setattr("nextprompt.diagnostics.subprocess.run", skip_stop)
    assert not check_hooks(ROOT)
