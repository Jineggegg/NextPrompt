# Changelog

## 0.1.4

- Keep the NextPrompt product name and existing six skill commands unchanged.
- Ask Y/N for automatic clipboard copy during Windows installation, save the
  choice, and report ON/automatic copy or OFF/display only at completion.
- Default empty interactive answers to display only; support explicit
  `-AutoCopy on|off` for unattended installation. Never infer consent from silence.
- Verify interactive choices against real isolated configuration writes, without
  changing the user's clipboard or trusting Hooks automatically.

## 0.1.3 — 2026-10-04

- Display suggestions immediately after plugin loading and Hook trust, without
  requiring setup. Default clipboard copy to off; preserve existing explicit settings
  and safely treat legacy unset settings as display only.
- Make setup optional for clipboard opt-in or other settings; do not gate unrelated
  configuration changes on a clipboard question.
- Show restart, Hook review/trust, first-use examples and optional setup instructions
  at the end of the Windows installer, with matching English and Chinese documentation.
- Exercise fresh-install, no-config Stop Hooks through real CLI integration tests.

## 0.1.2 — 2026-10-03

- Retry explicit model-unavailable errors with the next catalog-listed lightweight
  model at `low`, with one shared deadline and no authentication/quota/transport hopping.
- Default new configurations to `low`; preserve existing explicit reasoning choices.
- Make suggestions concise user-voice continuations with explicit approval boundaries.
- Test Windows prerequisite paths without real downloads, including broken App
  Execution Aliases, and make their version probes safely fall back to installation.
- Extend real CLI/local-service integration coverage to runtime model fallback.

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
