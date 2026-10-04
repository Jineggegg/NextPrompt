# Changelog

## Unreleased

- Optional inline mode (`setup --source inline`): a SessionStart Hook asks the Codex model
  to end each reply with a `Next prompt:` line, and the Stop Hook copies that line without
  a separate model request. Replies without a usable line fall back to the lightweight
  model. The default stays `--source model`.

## 0.1.8 — 2026-10-04

- Automatic clipboard copy is now on by default, including manual installs; the Windows
  installer defaults to Y (Enter) and N keeps display-only mode. Legacy unset settings
  follow the default; an explicit `auto_copy: false` is respected.
- Show a desktop notification with the suggestion as soon as it is copied (macOS,
  Windows/WSL toast, Linux `notify-send`), because the Codex desktop app does not show
  Hook messages in the conversation. Localized; `setup --notify off` disables it.
- Slimmer suggestion requests (14.3 KB → 8.8 KB with Codex 0.159/0.160): disable the
  `goals` feature and `request_user_input` tool, and omit Codex's sandbox and
  environment prose. Identical prefixes also help server-side prompt caching.
- The integration safety check now inspects tools sent inside Codex's
  `additional_tools` input item, which the previous check missed.
- Windows: retry the settings lock while a previous lock file is still being deleted
  ("access denied"), instead of failing concurrent settings updates.

## 0.1.7 — 2026-10-04

- Support Python 3.9 so the `python3` bundled with macOS (3.9.6) runs the Stop Hook.
  0.1.6 rejected it and every turn showed `hook: Stop Failed` without a suggestion.
- Doctor reports which interpreter the Hook will use (`python`, else `python3`) and
  fails when neither is Python 3.9+.
- CI also tests Python 3.9.

## 0.1.6 — 2026-10-04

- Fall back from `python` to `python3` in the Stop Hook so stock macOS and Linux
  (no `python` command) get suggestions instead of `hook: Stop Failed`. Interpreters
  older than 3.10 exit 1, never 2, so the fallback cannot request a continuation.
- Accept long Stop inputs up to 4 MiB; final answers over 64 KiB were silently skipped.
- Keep short Chinese, Japanese and Korean suggestions such as `运行全部测试`.
- Show the specific configuration error (stale lock, invalid or out-of-range
  setting) instead of a generic message; Doctor reports an invalid config and still
  runs its remaining checks.
- Report the package version consistently, including to Codex's app-server.
- Multilingual: labels follow the latest user message (Simplified/Traditional
  Chinese, Japanese, Korean, Russian) or a new `language` setting (also English,
  Spanish, French, German, Portuguese); the model writes in the user's latest language.
  Word limits count unspaced scripts by characters (about 40 Chinese characters),
  and generic-reply, assistant-voice and completed-work filters cover CJK and more.
- Cache the verified Codex CLI and model catalog for 12 hours after a successful
  suggestion, skipping three Codex startups per turn. Upgrades, model setting
  changes, rejected models and Doctor refresh it; it never stores conversation text.
- Strip inline code backticks from suggestions instead of discarding them.

## 0.1.5 — 2026-10-04

- Unify repository, package, marketplace, installation commands and display
  names as NextPrompt; the plugin is now installed as `nextprompt@nextprompt`.
- Simplify the README and move detailed reference material into `docs/GUIDE.md`.

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
