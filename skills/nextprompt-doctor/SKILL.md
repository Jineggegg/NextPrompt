---
name: nextprompt-doctor
description: Diagnose NextPrompt plugin layout, Codex CLI, model catalog and clipboard backend without exposing credentials. Use for NextPrompt Doctor or troubleshooting NextPrompt.
---

Resolve the installed plugin root from this SKILL.md path (two directories above
the containing directory). Run:

`python "<plugin root>/scripts/nextprompt.py" doctor`

The CLI uses `PLUGIN_DATA` or the official data path for marketplace
`nextprompt`. For a different marketplace supply its official `--data-dir`
before the command. This checks login status and model discovery without reading
credential files or conversation content. A login status check does not validate
the token or prove entitlement. A catalog entry does not prove inference access.

If the user requests a real inference test, add `--probe`. This uses only a
synthetic example and may consume account quota. Never show raw CLI errors,
tokens, full home paths or conversation dumps. Explain that hook trust must be
reviewed in the official Codex `/hooks` interface.

Exit code 1 indicates a failed required check, even when login status or the model
catalog looks healthy. On an authentication failure, ask the user to run Codex's
normal login flow on their own machine and retry the probe; do not inspect credentials.
A missing clipboard backend is informational and supports display-only operation.
