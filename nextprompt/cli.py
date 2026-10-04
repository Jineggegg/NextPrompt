"""Small CLI used by skills; clipboard consent is always explicit."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .clipboard import SystemClipboardAdapter
from .config import DEFAULTS, ConfigError, ConfigStore
from .hook import generate_suggestion
from .i18n import LANGUAGES
from .platform import detect_platform
from .process import run_process
from .providers import CodexSuggestionProvider, ProviderUnavailable, choose_model
from .transcript import Message


def status(cfg: dict[str, Any]) -> str:
    clipboard = SystemClipboardAdapter(osc52_fallback=cfg["clipboard"]["osc52_fallback"])
    auto = cfg["clipboard"]["auto_copy"]
    return "\n".join(
        [
            "NextPrompt",
            f"Enabled:          {'Yes' if cfg['enabled'] else 'No'}",
            f"Auto-copy:        {'No (display only)' if auto is False else 'Yes'}",
            f"Notification:     {'Yes' if cfg['notify'] else 'No'}",
            f"Model:            {cfg['model']['name']} (configured)",
            "Language:         "
            + ("auto (follows your messages)" if cfg["language"] == "auto" else cfg["language"]),
            f"Context:          Last {cfg['context']['last_messages']} messages",
            f"Max prompt:       {cfg['suggestion']['max_words']} words",
            f"Secret redaction: {'Enabled' if cfg['privacy']['redact_secrets'] else 'Disabled'}",
            f"Clipboard:        {detect_platform().label}",
            f"Backend:          {clipboard.backend_name()}",
        ]
    )


def hook_interpreter() -> tuple[str, str] | None:
    """The interpreter the Stop hook command will use: `python`, else `python3`."""
    for name in ("python", "python3"):
        executable = shutil.which(name)
        if not executable:
            continue
        try:
            result = run_process(
                [executable, "-c", "import sys;print('%d.%d.%d' % sys.version_info[:3])"],
                timeout=5,
            )
            version = result.stdout.decode("ascii").strip()
            if result.returncode == 0 and tuple(map(int, version.split(".")[:2])) >= (3, 9):
                return name, version
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue
    return None


@dataclass(frozen=True)
class DoctorReport:
    text: str
    healthy: bool


def doctor(store: ConfigStore, probe: bool = False) -> DoctorReport:
    rows = ["NextPrompt Doctor", "Python              ✓ " + sys.version.split()[0]]
    try:
        cfg = store.load()
        config_ok = True
        rows.append(
            "Config              ✓ "
            + ("configured" if store.path.exists() else "defaults ready (auto-copy on)")
        )
    except ConfigError as exc:
        # Hooks skip an invalid config; check the remaining setup with defaults.
        cfg, config_ok = deepcopy(DEFAULTS), False
        rows.append(f"Config              ✗ {exc}")
        rows.append("Action              Repair or delete NextPrompt config.json, then run setup.")
    root = Path(__file__).resolve().parents[1]
    try:
        manifest = json.loads((root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        hooks = json.loads((root / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        valid = manifest["name"] == "nextprompt" and set(hooks["hooks"]) == {"Stop"}
    except (OSError, ValueError, KeyError):
        valid = False
    interpreter = hook_interpreter()
    healthy = valid and config_ok and interpreter is not None
    rows.append(
        f"Hook Python         ✓ {interpreter[0]} {interpreter[1]}"
        if interpreter
        else "Hook Python         ✗ no python/python3 3.9+ on PATH (hook would fail)"
    )
    rows += [
        f"Plugin              {'✓' if valid else '✗'} bundle",
        f"Hook                {'✓' if valid else '✗'} Stop (review trust in /hooks)",
        "Re-entry protection ✓ hooks/plugins disabled + NEXTPROMPT_INTERNAL",
    ]
    provider = CodexSuggestionProvider(cfg["model"], store.root)
    provider.clear_cache()  # Doctor re-verifies everything; the next turn starts fresh.
    try:
        rows.append("Codex CLI           ✓ " + provider.check_cli().replace("codex-cli ", ""))
        auth = run_process([provider.executable(), "login", "status"], timeout=3)
        healthy = healthy and auth.returncode == 0
        text = (auth.stdout + auth.stderr).decode("utf-8", "replace").casefold()
        source = (
            "ChatGPT" if "chatgpt" in text else "API key" if "api key" in text else "configured"
        )
        rows.append(
            f"Authentication      {'✓' if auth.returncode == 0 else '✗'} "
            f"{source} (status only; token validity unverified)"
        )
        with tempfile.TemporaryDirectory(prefix="nextprompt-doctor-") as name:
            selection = choose_model(
                provider.discover_models(Path(name)),
                cfg["model"]["name"],
                cfg["model"]["reasoning"],
            )
        rows.append(f"Suggestion model    ✓ {selection.name} / {selection.reasoning} (catalog)")
        if probe:
            value = provider.generate(
                "USER:\nFix the login redirect.\n"
                "ASSISTANT:\nImplemented the fix. Targeted tests pass.\n"
            )
            from .suggestion import sanitize

            usable = bool(sanitize(value))
            healthy = healthy and usable
            rows.append(
                "Inference probe     "
                + ("✓ one short suggestion" if usable else "✗ invalid response")
            )
    except (ProviderUnavailable, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        healthy = False
        category = str(exc) if isinstance(exc, ProviderUnavailable) else "unavailable"
        category = category if category in ("authentication", "quota", "timeout") else "unavailable"
        label = "Inference probe" if probe else "Suggestion model"
        rows.append(f"{label:<20}✗ {category}")
        if category == "authentication":
            rows.append("Action              Run codex login on this machine, then retry --probe.")
    clipboard = SystemClipboardAdapter(osc52_fallback=cfg["clipboard"]["osc52_fallback"])
    rows.append(
        f"Clipboard backend   {'✓' if clipboard.available() else '—'} "
        + clipboard.backend_name()
        + " (detection only)"
    )
    rows.append("Platform            ✓ " + detect_platform().label)
    return DoctorReport("\n".join(rows), healthy)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="nextprompt")
    result.add_argument("--data-dir", type=Path, help="Explicit plugin data directory")
    commands = result.add_subparsers(dest="command", required=True)
    setup = commands.add_parser(
        "setup", help="Configure NextPrompt with explicit clipboard consent"
    )
    setup.add_argument("--auto-copy", choices=("on", "off"))
    setup.add_argument("--enabled", choices=("on", "off"))
    setup.add_argument("--model")
    setup.add_argument("--context-messages", type=int)
    setup.add_argument("--max-words", type=int)
    setup.add_argument("--redaction", choices=("on", "off"))
    setup.add_argument("--osc52", choices=("on", "off"))
    setup.add_argument("--notify", choices=("on", "off"))
    setup.add_argument("--trigger-mode", choices=("every_turn", "manual"))
    setup.add_argument("--language", choices=("auto", *LANGUAGES))
    for command in ("status", "enable", "disable"):
        commands.add_parser(command)
    check = commands.add_parser("doctor")
    check.add_argument("--probe", action="store_true", help="Run one synthetic inference request")
    suggest = commands.add_parser("suggest")
    suggest.add_argument(
        "--context-stdin",
        action="store_true",
        required=True,
        help='Read {"messages":[{"role":"user","text":"..."}]} from stdin',
    )
    return result


def run(args: argparse.Namespace) -> int:
    store = ConfigStore(args.data_dir)
    if args.command == "setup":
        settings_requested = any(
            getattr(args, key) is not None
            for key in (
                "enabled",
                "model",
                "context_messages",
                "max_words",
                "redaction",
                "osc52",
                "notify",
                "trigger_mode",
                "language",
            )
        )
        if args.auto_copy is None and not settings_requested:
            if not sys.stdin.isatty():
                print("Setup requires explicit --auto-copy on or --auto-copy off.")
                return 2
            print(
                "NextPrompt Setup\nAutomatically copy suggested next prompts to your clipboard?\n"
                "Default: Yes\n1. Yes — automatically copy suggestions\n"
                "2. No  — display suggestions only"
            )
            while args.auto_copy is None:
                answer = input("Choose 1 or 2 [1]: ").strip().casefold()
                if answer in ("", "1", "yes", "y"):
                    args.auto_copy = "on"
                elif answer in ("2", "no", "n"):
                    args.auto_copy = "off"

        def configure(cfg: dict[str, Any]) -> None:
            mappings = (
                ("auto_copy", "clipboard", "auto_copy", lambda v: v == "on"),
                ("osc52", "clipboard", "osc52_fallback", lambda v: v == "on"),
                ("model", "model", "name", str),
                ("context_messages", "context", "last_messages", int),
                ("max_words", "suggestion", "max_words", int),
                ("redaction", "privacy", "redact_secrets", lambda v: v == "on"),
            )
            for attr, section, key, convert in mappings:
                if (value := getattr(args, attr)) is not None:
                    cfg[section][key] = convert(value)
            if args.enabled is not None:
                cfg["enabled"] = args.enabled == "on"
            if args.trigger_mode is not None:
                cfg["trigger_mode"] = args.trigger_mode
            if args.language is not None:
                cfg["language"] = args.language
            if args.notify is not None:
                cfg["notify"] = args.notify == "on"

        cfg = store.update(configure)
        print("NextPrompt configured.\n" + status(cfg))
        print(
            "Next suggestions will be copied automatically after completed Codex turns."
            if cfg["clipboard"]["auto_copy"] is not False
            else "Next suggestions will be displayed only."
        )
    elif args.command in ("enable", "disable"):
        enabled = args.command == "enable"
        store.update(lambda cfg: cfg.update(enabled=enabled))
        print(f"NextPrompt {'enabled' if enabled else 'disabled'}.")
    elif args.command == "status":
        print(status(store.load()))
    elif args.command == "doctor":
        report = doctor(store, args.probe)
        print(report.text)
        return 0 if report.healthy else 1
    elif args.command == "suggest":
        cfg = store.load()
        if not cfg["enabled"]:
            return 0
        data = sys.stdin.buffer.read(524289)
        if len(data) > 524288:
            return 0
        raw = json.loads(data)
        entries = raw.get("messages", []) if isinstance(raw, dict) else []
        messages = [
            Message(m["role"], m["text"])
            for m in entries
            if isinstance(m, dict)
            and m.get("role") in ("user", "assistant")
            and isinstance(m.get("text"), str)
        ]
        text = generate_suggestion(messages, cfg, store)
        if text:
            print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        return run(args)
    except (Exception, KeyboardInterrupt) as exc:
        if args.command == "suggest":
            return 0
        if isinstance(exc, ConfigError):
            # Fixed, content-free messages, e.g. a stale lock or out-of-range setting.
            print(f"NextPrompt configuration error: {exc}.")
        else:
            print("NextPrompt unavailable. Check configuration with nextprompt doctor.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
