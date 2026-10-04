"""UserPromptSubmit entrypoint: in inline mode, remind the root model of the last line."""

import os
import sys

if os.environ.get("NEXTPROMPT_INTERNAL") == "1":
    raise SystemExit(0)

# Exit 1 (never 2) on an unsupported interpreter so `python || python3` falls back.
if sys.version_info < (3, 9):  # noqa: UP036 - runtime guard for older interpreters
    raise SystemExit(1)

MAX_PAYLOAD = 4 * 1024 * 1024

try:
    import json
    from pathlib import Path

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nextprompt.hook import handle_user_prompt_submit

    raw = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
    if len(raw) <= MAX_PAYLOAD:
        text = handle_user_prompt_submit(json.loads(raw))
        if text:
            # Additional context only: no decision, reason, or continue:false.
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": text,
                }
            }
            sys.stdout.buffer.write((json.dumps(output, ensure_ascii=False) + "\n").encode("utf-8"))
except Exception:
    pass
