"""Run installed hook commands on synthetic inputs in a disposable data directory."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .config import ConfigStore


def check_hooks(root: Path) -> bool:
    """Exercise the real shell launcher without inference, notifications or clipboard writes."""
    try:
        hooks = json.loads((root / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
        with tempfile.TemporaryDirectory(prefix="nextprompt-hook-check-") as name:
            data = Path(name)
            ConfigStore(data).update(
                lambda cfg: (cfg.update(notify=False), cfg["clipboard"].update(auto_copy=False))
            )
            env = {**os.environ, "PLUGIN_ROOT": str(root), "PLUGIN_DATA": name}
            env.pop("NEXTPROMPT_INTERNAL", None)
            payloads = (
                {"hook_event_name": "SessionStart", "source": "startup"},
                {"hook_event_name": "UserPromptSubmit", "prompt": "Write part one only."},
                {
                    "hook_event_name": "Stop",
                    "last_assistant_message": (
                        "Part one is ready.\n\n→ Want me to “write part two”?"
                    ),
                },
            )
            for payload in payloads:
                event = payload["hook_event_name"]
                command = hooks[event][0]["hooks"][0]["command"]
                result = subprocess.run(
                    command,
                    shell=True,
                    input=json.dumps({**payload, "session_id": "doctor"}).encode("utf-8"),
                    capture_output=True,
                    env=env,
                    cwd=root,
                    timeout=15,
                    check=False,
                )
                if result.returncode != 0:
                    return False
                output = result.stdout.decode("utf-8-sig")
                if event == "SessionStart":
                    context = json.loads(output)["hookSpecificOutput"]["additionalContext"]
                    if "NextPrompt is installed." not in context:
                        return False
                elif event == "UserPromptSubmit" and "NextPrompt:" not in output:
                    return False
            # A launcher returning success without running Python must not pass.
            counts = json.loads((data / ".stats.json").read_text(encoding="utf-8"))
            return counts["replies"] == 1 and counts["suggested"] == 1
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.TimeoutExpired):
        return False
