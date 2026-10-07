"""Opt-in authenticated model-mode evaluation, using only synthetic fixture messages."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nextprompt.config import DEFAULTS, ConfigStore  # noqa: E402
from nextprompt.hook import handle_stop  # noqa: E402
from nextprompt.providers import CodexSuggestionProvider, ProviderUnavailable  # noqa: E402
from nextprompt.transcript import Message  # noqa: E402


class RecordingProvider(CodexSuggestionProvider):
    raw: str | None = None
    error: str | None = None

    def generate(self, context):
        try:
            self.raw = super().generate(context)
            return self.raw
        except ProviderUnavailable as error:
            self.error = str(error)
            raise


def evaluate(case, model, home, output, repeat):
    store = ConfigStore(home / f"{case['id']}-{repeat}")
    store.update(
        lambda cfg: (
            cfg.update(source="model", notify=False, stats=False),
            cfg["model"].update(name=model),
        )
    )
    provider = RecordingProvider(store.load()["model"], store.root)
    copies = []
    clipboard = Mock(
        available=Mock(return_value=True),
        backend_name=Mock(return_value="scenario-receiver"),
        copy=Mock(side_effect=lambda text: copies.append(text) or True),
    )
    messages = [Message(**message) for message in case["messages"]]
    started = time.monotonic()
    result = handle_stop(
        {
            "hook_event_name": "Stop",
            "last_assistant_message": messages[-1].text,
            "transcript_path": "synthetic.jsonl",
        },
        store=store,
        provider=provider,
        clipboard=clipboard,
        conversation=Mock(read=Mock(return_value=messages)),
    )
    flags = []
    if provider.error:
        flags.append("runtime:" + provider.error)
    if case["expect"] == "required" and not copies:
        flags.append("missing_suggestion")
    if case["expect"] == "forbidden" and copies:
        flags.append("unwanted_suggestion")
    if copies and case.get("target") and not re.search(case["target"], copies[0], re.I):
        flags.append("wrong_target")
    row = {
        "case": case["id"],
        "repeat": repeat,
        "expect": case["expect"],
        "messages": case["messages"],
        "copies": copies,
        "flags": flags,
        "seconds": round(time.monotonic() - started, 2),
        "result": result,
        "raw": provider.raw,
        "error": provider.error,
        "model": provider.selection.name if provider.selection else None,
    }
    (output / f"{case['id']}-{repeat}.json").write_text(
        json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: row[key] for key in ("case", "repeat", "flags", "seconds")}), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULTS["model"]["name"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=("model", "model_heldout"), default="model")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "docs/benchmarks/scenarios.json").read_text(encoding="utf-8"))[
        args.split
    ]
    previous_home = os.environ.get("CODEX_HOME")
    active = Path(previous_home or str(Path.home() / ".codex"))
    with tempfile.TemporaryDirectory(dir=args.output, prefix="isolated-") as directory:
        home = Path(directory)
        if (active / "auth.json").is_file():
            (home / "auth.json").symlink_to(active / "auth.json")
        os.environ["CODEX_HOME"] = str(home)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = [
                    pool.submit(evaluate, case, args.model, home, args.output, repeat)
                    for repeat in range(args.repeat)
                    for case in cases
                ]
                rows = [future.result() for future in concurrent.futures.as_completed(futures)]
        finally:
            if previous_home is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = previous_home
    report = {"model": args.model, "cases": len(rows), "flags": sum(bool(r["flags"]) for r in rows)}
    (args.output / "report.json").write_text(
        json.dumps({**report, "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))
    raise SystemExit(bool(report["flags"]))


if __name__ == "__main__":
    main()
