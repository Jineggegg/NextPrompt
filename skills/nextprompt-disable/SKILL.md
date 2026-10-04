---
name: nextprompt-disable
description: Disable NextPrompt immediately. Use for Disable NextPrompt.
---

Resolve the plugin root from this installed SKILL.md path (two directories above
its containing directory). Run:

`python "<plugin root>/scripts/nextprompt.py" disable`

The CLI uses `PLUGIN_DATA` or the official data path for marketplace
`nextprompt`. For a different marketplace supply its official `--data-dir`
before the command. Show the result. Do not read conversation files, invoke
inference, or copy anything. Subsequent Stop hooks exit after reading the enabled flag.
