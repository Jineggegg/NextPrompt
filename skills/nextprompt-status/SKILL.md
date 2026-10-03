---
name: nextprompt-status
description: Show NextPrompt settings and clipboard backend. Use for Show NextPrompt status.
---

Resolve the installed plugin root from this skill's absolute file path (two
directories above the containing directory). Run:

`python "<plugin root>/scripts/nextprompt.py" status`

Use `PLUGIN_DATA` if available; otherwise the default official data path is for
marketplace `codex-prompty`. For a different marketplace supply its official
`--data-dir` before `status`. Display the output. Do not read transcripts or credentials.
