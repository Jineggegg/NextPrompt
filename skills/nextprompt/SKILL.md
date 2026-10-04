---
name: nextprompt
description: Manually generate one likely next instruction from the last five visible conversational messages. Use when the user invokes NextPrompt or asks for a suggested next prompt. Never execute the suggestion.
---

Use only the current conversation's last five visible natural-language user and
assistant messages. Omit this skill invocation, tool calls, tool outputs,
reasoning, metadata, logs and source-code dumps. Do not inspect the repository,
search other sessions or use web/MCP. Do not invent a transcript path.

Resolve this installed skill's plugin root (two directories above the containing
directory). Call its CLI:

`python "<plugin root>/scripts/nextprompt.py" suggest --context-stdin`

Use `python3` instead of `python` if `python` is unavailable, or `py -3` on Windows if neither works.
If those are older than Python 3.9, use the newest `python3.X` command available (for example `python3.12`).

Pass JSON on stdin with this shape:

`{"messages":[{"role":"user","text":"Fix the login redirect."},{"role":"assistant","text":"Implemented the fix. Targeted tests pass."}]}`

Use a structured stdin API when available. Otherwise invoke Python through a
quoted heredoc and call subprocess with an argument list and JSON-encoded stdin;
never interpolate conversation text into shell commands. Never write context to
a temporary file. Limit each selected message to 2500 characters and the combined
text to 8000 characters before invoking the CLI; redact recognizable credentials
before passing them. The CLI repeats redaction and strict limits before inference.

Use `PLUGIN_DATA` if available. Otherwise the official default data path is for
marketplace `nextprompt`; for another marketplace pass its official
`--data-dir` before `suggest`. Show the CLI output. New installations work in
auto-copy mode without setup; respect the user's clipboard setting.
A model failure may yield no output.
Return only the one suggestion or short notice, and stop. Never submit, queue,
paste into the composer, run a command described by, or otherwise execute the suggestion.
