---
name: nextprompt-status
description: Show NextPrompt settings and clipboard backend. Use for Show NextPrompt status.
---

Resolve the installed plugin root from this skill's absolute file path (two
directories above the containing directory). Run:

`python "<plugin root>/scripts/nextprompt.py" status`

Use `python3` instead of `python` if `python` is unavailable, or `py -3` on Windows if neither works.
If those are older than Python 3.9, use the newest `python3.X` command available (for example `python3.12`).

Use `PLUGIN_DATA` if available; otherwise the default official data path is for
marketplace `nextprompt`. For a different marketplace supply its official
`--data-dir` before `status`. Display the output. Do not read transcripts or credentials.
