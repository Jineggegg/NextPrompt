"""Entrypoint: exit zero even on malformed input, config or provider failures."""

import os
import sys

if os.environ.get("NEXTPROMPT_INTERNAL") == "1":
    raise SystemExit(0)

# An unsupported interpreter exits 1 (never 2, which would continue the turn) so
# the hook command can fall back to the next interpreter it lists.
if sys.version_info < (3, 9):  # noqa: UP036 - runtime guard for older interpreters
    raise SystemExit(1)

# Stop input carries last_assistant_message; leave room for long final answers.
MAX_PAYLOAD = 4 * 1024 * 1024

try:
    import json
    from pathlib import Path

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nextprompt.hook import handle_stop
    from nextprompt.output import CodexHookOutputAdapter

    raw = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
    if len(raw) <= MAX_PAYLOAD:
        message = handle_stop(json.loads(raw))
        if message:
            sys.stdout.buffer.write(
                (CodexHookOutputAdapter().encode(message) + "\n").encode("utf-8")
            )
except Exception:
    pass
