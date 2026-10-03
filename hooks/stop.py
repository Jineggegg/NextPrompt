"""Entrypoint: exit zero even on malformed input, config or provider failures."""

import os

if os.environ.get("NEXTPROMPT_INTERNAL") == "1":
    raise SystemExit(0)

try:
    import json
    import sys
    from pathlib import Path

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nextprompt.hook import handle_stop
    from nextprompt.output import CodexHookOutputAdapter

    raw = sys.stdin.buffer.read(65537)
    if len(raw) <= 65536:
        message = handle_stop(json.loads(raw))
        if message:
            sys.stdout.buffer.write(
                (CodexHookOutputAdapter().encode(message) + "\n").encode("utf-8")
            )
except Exception:
    pass
