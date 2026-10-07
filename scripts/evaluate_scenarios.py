"""Opt-in real-model, real-Codex scenario evaluation. Never uses the desktop clipboard.

Only synthetic cases belong in the input/results. Uses existing Codex login through a
symlink in a disposable CODEX_HOME, without opening or copying credentials.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nextprompt.hook import asks_user, inline_suggestion  # noqa: E402
from nextprompt.i18n import go_ahead  # noqa: E402
from nextprompt.providers import failure_category  # noqa: E402

OBSERVER = r"""
import io, json, os, runpy, sys, time
from pathlib import Path
root = Path(os.environ['PLUGIN_ROOT'])
sys.path.insert(0, str(root))
import nextprompt.hook as hook
raw = sys.stdin.buffer.read()
payload = json.loads(raw)
copies, notifications = [], []
class Receiver:
    def __init__(self, **kwargs): pass
    def available(self): return True
    def copy(self, text): copies.append(text); return True
    def backend_name(self): return 'scenario-receiver'
hook.SystemClipboardAdapter = Receiver
hook.send_notification = lambda title, body: notifications.append((title, body)) or True
original = sys.stdout
sys.stdin = io.TextIOWrapper(io.BytesIO(raw), encoding='utf-8')
sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding='utf-8')
runpy.run_path(str(root / 'hooks' / sys.argv[1]), run_name='__main__')
sys.stdout.flush()
output = sys.stdout.buffer.getvalue()
sys.stdout = original
record = {'event': payload.get('hook_event_name'), 'payload': payload,
          'output': output.decode('utf-8'), 'copies': copies, 'notifications': notifications}
Path(sys.argv[2], str(time.time_ns()) + '.json').write_text(json.dumps(record, ensure_ascii=False))
sys.stdout.buffer.write(output)
"""


def run_session(case, model, effort, output, repeat):
    identifier = f"{case['id']}-{repeat}"
    results = []
    active_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    with tempfile.TemporaryDirectory(prefix=identifier + "-", dir=output) as temporary:
        work = Path(temporary)
        home, receipts = work / "home", work / "receipts"
        home.mkdir()
        receipts.mkdir()
        auth = active_home / "auth.json"
        if auth.is_file():
            (home / "auth.json").symlink_to(auth)
        env = {**os.environ, "CODEX_HOME": str(home)}
        for key in ("PLUGIN_DATA", "PLUGIN_ROOT", "NEXTPROMPT_INTERNAL"):
            env.pop(key, None)
        config = {
            "approval_policy": "never",
            "sandbox_mode": "read-only",
            "model": model,
            "model_reasoning_effort": effort,
            "web_search": "disabled",
            "project_doc_max_bytes": 0,
            "skills.include_instructions": False,
            "features.skip_host_skill_discovery": True,
            "agents.enabled": False,
            "analytics.enabled": False,
        }
        (home / "config.toml").write_text(
            "\n".join(f"{key} = {json.dumps(value)}" for key, value in config.items()) + "\n"
        )
        for args in (("marketplace", "add", str(ROOT)), ("add", "nextprompt@nextprompt")):
            install = subprocess.run(
                ["codex", "plugin", *args, "--json"],
                env=env,
                cwd=work,
                capture_output=True,
                timeout=30,
                check=True,
            )
        installed = Path(json.loads(install.stdout)["installedPath"])
        observer = work / "observer.py"
        observer.write_text(OBSERVER)
        manifest = installed / "hooks/hooks.json"
        hooks = json.loads(manifest.read_text())
        for event, groups in hooks["hooks"].items():
            entry = "stop.py" if event == "Stop" else "context.py"
            groups[0]["hooks"][0]["command"] = " ".join(
                shlex.quote(str(arg)) for arg in (sys.executable, observer, entry, receipts)
            )
        manifest.write_text(json.dumps(hooks))
        base = ["codex", "exec"]
        shared = ["--json", "--skip-git-repo-check", "--dangerously-bypass-hook-trust"]
        for feature in (
            "apps",
            "shell_tool",
            "multi_agent",
            "multi_agent_v2",
            "browser_use",
            "browser_use_external",
            "computer_use",
            "image_generation",
            "view_image",
            "memories",
            "sleep_tool",
            "tool_suggest",
            "goals",
        ):
            shared += ["--disable", feature]
        session = None
        for index, turn in enumerate(case["turns"]):
            prior = set(receipts.iterdir())
            args = [*base, *([] if session is None else ["resume", session]), *shared, "-"]
            start = time.monotonic()
            try:
                result = subprocess.run(
                    args,
                    input=turn["prompt"].encode(),
                    capture_output=True,
                    env=env,
                    cwd=work,
                    timeout=240,
                )
                events = []
                for line in result.stdout.splitlines():
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        pass
                for event in events:
                    if event.get("type") == "thread.started":
                        session = event["thread_id"]
                replies = [
                    event["item"].get("text", "")
                    for event in events
                    if event.get("type") == "item.completed"
                    and event.get("item", {}).get("type") == "agent_message"
                ]
                reply = replies[-1] if replies else ""
                records = [
                    json.loads(p.read_text()) for p in sorted(set(receipts.iterdir()) - prior)
                ]
                stops = [r for r in records if r["event"] == "Stop"]
                copies = [value for record in stops for value in record["copies"]]
                notices = [value for record in stops for value in record["notifications"]]
                suggestion = inline_suggestion(reply)
                flags = []
                if result.returncode or not reply:
                    flags.append("runtime:" + failure_category(result.stderr))
                if len(stops) != 1:
                    flags.append("stop_count:" + str(len(stops)))
                if turn["expect"] == "required" and not suggestion:
                    flags.append("missing_suggestion")
                if turn["expect"] == "forbidden" and (suggestion or copies):
                    flags.append("unwanted_suggestion")
                if suggestion and turn.get("target") and not re.search(turn["target"], suggestion):
                    flags.append("wrong_target")
                if suggestion and not copies:
                    flags.append("shown_not_copied")
                if copies and not suggestion:
                    flags.append("copied_without_suggestion")
                if suggestion and len(copies) > 1:
                    flags.append("multiple_copies")
                if suggestion and copies and copies != [go_ahead(suggestion)]:
                    flags.append("wrong_copied_text")
                if len(notices) != len(copies):
                    flags.append("notification_count")
                row = {
                    "session": case["id"],
                    "repeat": repeat,
                    "turn": index + 1,
                    "prompt": turn["prompt"],
                    "expect": turn["expect"],
                    "reply": reply,
                    "suggestion": suggestion,
                    "copies": copies,
                    "notifications": notices,
                    "asks_user": asks_user(reply),
                    "flags": flags,
                    "seconds": round(time.monotonic() - start, 2),
                    "hook_events": [r["event"] for r in records],
                    "usage": [e.get("usage") for e in events if e.get("type") == "turn.completed"],
                }
            except subprocess.TimeoutExpired:
                row = {
                    "session": case["id"],
                    "repeat": repeat,
                    "turn": index + 1,
                    "prompt": turn["prompt"],
                    "expect": turn["expect"],
                    "flags": ["timeout"],
                }
            results.append(row)
            print(
                json.dumps({key: row.get(key) for key in ("session", "turn", "flags", "seconds")}),
                flush=True,
            )
            (output / f"{identifier}.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2)
            )
            if not session:
                break
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", default="xhigh")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("sessions", "heldout", "stress"), default="sessions")
    parser.add_argument("--select", default="")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "docs/benchmarks/scenarios.json").read_text())[args.split]
    if args.select:
        cases = [case for case in cases if case["id"] in args.select.split(",")]
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(run_session, case, args.model, args.effort, args.output, repeat)
            for repeat in range(args.repeat)
            for case in cases
        ]
        for future in concurrent.futures.as_completed(futures):
            rows.extend(future.result())
    report = {
        "model": args.model,
        "reasoning": args.effort,
        "turns": len(rows),
        "flags": sum(bool(row["flags"]) for row in rows),
        "results": rows,
    }
    (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "results"}))
    raise SystemExit(bool(report["flags"]))


if __name__ == "__main__":
    main()
