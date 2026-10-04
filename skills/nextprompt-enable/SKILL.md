---
name: nextprompt-enable
description: Enable NextPrompt suggestions. Use for Enable NextPrompt.
---

Resolve the plugin root from this installed SKILL.md path (two directories above
its containing directory). Run:

`python "<plugin root>/scripts/nextprompt.py" enable`

Use `python3` instead of `python` if `python` is unavailable, or `py -3` on Windows if neither works.
If those are older than Python 3.9, use the newest `python3.X` command available (for example `python3.12`).

The CLI uses `PLUGIN_DATA` or the official data path for marketplace
`nextprompt`. For a different marketplace supply its official `--data-dir`
before the command. Enabling suggestions does not change the clipboard setting.
Show the result. Never execute a recommended next prompt.
