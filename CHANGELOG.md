# Changelog

## 0.1.1 — 2026-10-03

- Add an explicit Windows PowerShell installer for Python prerequisite detection,
  user-scoped Python 3.12 installation through the official `winget` source, PATH
  refresh, plugin registration and Doctor verification.
- Keep all runtime and Hook paths non-installing, non-elevated and fail-closed when
  `winget` or Python verification is unavailable.
- Document the Windows quick install and the manual cross-platform path.

## 0.1.0 — 2026-10-03

- Official legacy Codex plugin, root Stop hook and six operation skills.
- Bounded last-five context, secret redaction and one-sentence sanitization.
- Model discovery with lightweight fallbacks and low reasoning.
- Isolated ephemeral inference, deadlines, fail-open handling and re-entry guards.
- Explicit clipboard consent; Windows/WSL/macOS/Wayland/X11 adapters and opt-in OSC 52.
- Atomic plugin-local config, setup notice and error cooldown.
- Unit tests, opt-in real CLI/local-model integration, docs and cross-platform CI.
- Doctor failure exit codes and safe authentication/quota diagnostics.
- Private GitHub checkout installation and a local validation checklist.

Private source preview: remote inference entitlement and real desktop clipboard
round trips remain unverified. Portable root plugin manifest hooks are skipped by
the examined Codex runtime; this version uses the official working legacy format.
