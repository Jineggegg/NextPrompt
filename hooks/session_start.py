"""SessionStart entrypoint: in inline mode, print the instruction the root model follows."""

import os
import sys

if os.environ.get("NEXTPROMPT_INTERNAL") == "1":
    raise SystemExit(0)

# Exit 1 (never 2) on an unsupported interpreter so `python || python3` falls back.
if sys.version_info < (3, 9):  # noqa: UP036 - runtime guard for older interpreters
    raise SystemExit(1)

MAX_PAYLOAD = 1024 * 1024

try:
    import json
    from pathlib import Path

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nextprompt.hook import handle_session_start

    raw = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
    if len(raw) <= MAX_PAYLOAD:
        text = handle_session_start(json.loads(raw))
        if text:
            # Plain stdout from SessionStart becomes developer context for the root model.
            sys.stdout.buffer.write((text + "\n").encode("utf-8"))
except Exception:
    pass
