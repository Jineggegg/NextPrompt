---
name: nextprompt-onboarding
description: Introduce and activate Codex Next Prompt after installation, or repair an installation whose automatic suggestions or hooks never started.
---

Start with a short introduction in the user's language, before running commands:
NextPrompt suggests one follow-up only for unfinished work the user already requested.
When it has a suggestion, the reply ends with a `→` line. Only the quoted instruction
is copied; the user reviews, pastes and sends it. Copy and desktop notifications are
on by default, and `$nextprompt-setup` can change them. A completed task or a question
that has been answered normally has no suggestion.

Resolve the plugin root two directories above this skill's containing directory.
Keep the existing installation and settings. Do not clone another copy or reinstall
just to show this introduction.

- On Windows, use PowerShell to dot-source `<plugin root>/scripts/python.ps1`, then
  call `Get-CompatiblePython`. It finds Python even when the app's PATH is stale.
  If it is missing, run `<plugin root>/scripts/install.ps1 -AutoCopy on -Notify on`
  with `powershell -NoProfile -ExecutionPolicy Bypass -File`. This installs the
  prerequisite and plugin. Respect any preferences the user already chose.
- On macOS/Linux, locate Python 3.9+ (`python3`, or a versioned `python3.X`). If missing,
  use `<plugin root>/scripts/install.sh --auto-copy on --notify on` with the same
  preference rule.
- Run `<python> <plugin root>/scripts/nextprompt.py doctor`. The default inline mode
  needs no separate model request. Do not run `--probe` unless the user asks for it.
  Use the active plugin's `PLUGIN_DATA`; for another marketplace pass its actual
  data directory with `--data-dir` before the command.

Report exactly what passed and what remains. Hook self-tests prove the commands
can run, not that this chat's hooks are trusted. Explain how to fully quit and reopen
Codex, then review and trust NextPrompt's SessionStart, UserPromptSubmit and Stop in
the client's Hooks settings (CLI: `/hooks`). Never edit trusted hashes, disable trust
checks, or change system execution policy. If the shell is WSL, its Python and
clipboard environment may differ from the Windows host; use the host where hooks run.

For a simple first-use example, suggest the user try “Write a two-part outline;
write only part one for now.” A follow-up for part two is expected. Do not submit it
or change the clipboard merely to demonstrate it. Do not claim end-to-end success
until a real suggestion and copy result have been observed.
