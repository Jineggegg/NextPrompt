---
name: nextprompt-setup
description: Configure NextPrompt, turn automatic clipboard copy or desktop notifications on or off, change the model, display language, context limits or OSC 52 settings. Use for Configure NextPrompt or Turn NextPrompt clipboard copy off.
---

Locate this installed skill's absolute SKILL.md path. The plugin root is two
directories above its containing directory. Run Python at `<plugin root>/scripts/nextprompt.py`.
Use `python3` instead of `python` if `python` is unavailable, or `py -3` on Windows if neither works.
Use `PLUGIN_DATA` if available. Otherwise the CLI derives the official legacy
plugin data path for marketplace `nextprompt`; if installed through a different
marketplace, pass `--data-dir` with its official plugin data directory before the command.
Never store settings inside the user's project. Never inspect credential files.

Setup is optional: new installations already copy each suggestion and show a desktop
notification.
If the user only requests another setting (such as a model or context limit),
apply that setting without changing clipboard behavior or asking an unrelated question.
If the user already explicitly chose clipboard on/off, apply that choice directly.
For a general setup request or a request to choose clipboard behavior, show this
question and wait for their answer:

NextPrompt Setup
Automatically copy suggested next prompts to your clipboard?
Default: Yes
1. Yes — automatically copy suggestions
2. No  — display suggestions only

An empty answer keeps the default (Yes). After a Yes answer run:

`python "<plugin root>/scripts/nextprompt.py" setup --auto-copy on`

After a No answer run the same command with `--auto-copy off`.
Do not pipe an interactive question into a tool. The flags work non-interactively.

Optional user-requested settings: `--enabled on|off`, `--model MODEL`,
`--context-messages 1..5`, `--max-words 1..20`, `--redaction on|off`,
`--osc52 on|off`, `--notify on|off` (desktop notification), `--trigger-mode every_turn|manual`,
`--language auto|en|zh|zh-TW|ja|ko|es|fr|de|pt|ru` (labels; `auto` follows the
user's latest message), `--source inline|model` (`inline`, the default: the Codex model ends each
reply with a next-step line in the user's language (`Next prompt:`, `下一步建议：`, …)
whose text is copied as is; `model`:
no line in replies, a separate lightweight request instead; takes effect in new or
resumed sessions). OSC 52 defaults off and is
unverified best effort; clipboard contents can be read by other local applications.
Show the CLI's concise configuration result. Never generate or execute a coding task.
