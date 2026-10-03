---
name: nextprompt-enable
description: Enable NextPrompt suggestions. Use for Enable NextPrompt.
---

Resolve the plugin root from this installed SKILL.md path (two directories above
its containing directory). Run:

`python "<plugin root>/scripts/nextprompt.py" enable`

The CLI uses `PLUGIN_DATA` or the official data path for marketplace
`codex-prompty`. For a different marketplace supply its official `--data-dir`
before the command. Enabling suggestions does not grant clipboard consent.
Show the result. Never execute a recommended next prompt.
