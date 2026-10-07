"""SessionStart / UserPromptSubmit entrypoint: inline-mode context for the root model."""

import os
import sys

if os.environ.get("NEXTPROMPT_INTERNAL") == "1":
    raise SystemExit(0)

# Exit 1 (never 2) on an unsupported interpreter so the hook command tries the next one.
if sys.version_info < (3, 9):  # noqa: UP036 - runtime guard for older interpreters
    raise SystemExit(1)

MAX_PAYLOAD = 1024 * 1024

try:
    import json
    from pathlib import Path

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nextprompt.hook import first_run_report, handle_context

    raw = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
    if len(raw) <= MAX_PAYLOAD:
        payload = json.loads(raw)
        text = handle_context(payload)
        report = first_run_report(payload)
        if report:
            # A systemMessage is shown in the UI. Keep the inline instruction as
            # developer context instead of relying on the model to relay onboarding.
            result = {"systemMessage": report}
            if text:
                result["hookSpecificOutput"] = {
                    "hookEventName": payload["hook_event_name"],
                    "additionalContext": text,
                }
            sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
        elif text:
            # Plain stdout from these events becomes developer context for the root model.
            sys.stdout.buffer.write((text + "\n").encode("utf-8"))
except Exception:
    pass
