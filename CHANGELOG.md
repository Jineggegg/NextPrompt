# Changelog

## 0.2.4 — 2026-10-08

- Doctor now accepts a valid no-suggestion response to its completed-task probe.
  Correct silence no longer reports a failed installation or model response.
  Invalid responses and authentication failures still fail the check.
- Clamp deadline calculations to their configured limit when coarse clocks round
  upward, preserving the 15-second inference cap on Windows Python 3.9.

## 0.2.3 — 2026-10-08

- Ignore suggestions inside Markdown code blocks, quoted examples and indented code;
  reject ambiguous lines containing more than one quoted instruction.
- Distinguish quoted or labelled fictional dialogue from a real request for the user
  to choose; cover English preference questions as well as Chinese choices.
- Align separate-model suggestions with the same unfinished-work policy as inline
  suggestions. Validate a structured instruction-or-null response and reject malformed
  output and prediction commentary before copying. Preserve existing model settings.
- Explicitly disable child agents in separate inference, including models whose
  catalog enables newer agent tooling by default.
- Add reproducible opt-in real-model suites for multi-turn conversations, topic and
  difficulty changes, long writing, interruptions, quotations and user boundaries.
- Hook command definitions are unchanged from 0.2.2.

## 0.2.2 — 2026-10-07

- Add a Codex Setup action with a first-use introduction and activation checks,
  independent of hooks; also show the one-time welcome after installation mid-chat.
- Use system PowerShell and shared Python discovery on Windows, including default
  install folders before PATH, avoiding stale PATH and Store alias failures.
- Run real hook commands in Doctor with isolated synthetic input. Inline mode no
  longer blocks installation on an unnecessary separate login or model lookup.
- Support WSLg clipboard copy when Windows executable interoperability is disabled.
- Report missing Python and WSL clipboard limitations with recovery steps; do not
  claim a loaded hook proves all hooks are trusted or clipboard copy works.

## 0.2.1 — 2026-10-05

- Windows: hooks no longer fail when Python is off the PATH Codex started with (for example
  Python installed after Codex was opened, or installed without "Add to PATH"). After the
  PATH commands, the hook command tries the per-user py launcher, the Python install
  manager and `%LOCALAPPDATA%\Programs\Python\Python3X\python.exe`. Doctor checks the same
  locations.
- README: an install prompt to paste into Codex, so the Codex app installs the plugin with a
  single approval, without a separate Codex CLI.
- Windows: the installer and Doctor use the Codex app's own `codex.exe`
  (`%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe`, newest first) when no `codex` command is on
  PATH, so `install.ps1` works from a normal PowerShell or Command Prompt with only the app
  installed instead of stopping with "Codex CLI is required".

## 0.2.0 — 2026-10-05

- Renamed to **Codex Next Prompt**; the repository is now `Jineggegg/codex-next-prompt`
  (old URLs redirect). Commands, the `nextprompt` package and the plugin id are unchanged.
- README is English only; the Chinese installation guide (`docs/LOCAL_TEST.md`) was removed
  in favor of `docs/GUIDE.md`.
- CI also runs on GitHub-hosted Windows and macOS (Python 3.9 and 3.14), and only once per
  PR push.
- SECURITY.md: the Windows installer section now matches `scripts/install.ps1`
  (Python 3.9+, and the signature-checked python.org fallback when `winget` is
  unavailable).
- Suggestions only when they help: the Codex model writes a suggestion line only for three
  kinds of step: a part the user named or planned that is not done yet (the next chapter,
  page or day, including parts left for later), finishing what this turn left unfinished or
  only diagnosed, and resuming unfinished work after a side question. New ideas
  (improvements, extra features, more checks), confirmations, answers, chatting, stopping
  and wrapping up get no line. A reply without a line copies nothing and no longer starts
  the fallback model (it still runs when Codex sends no reply text, and with
  `--source model`).
- Varied, natural wording: the line is the model's own sentence around one quoted prompt,
  such as `→ 要不要「接着写第三章」？` or `→ One loose end: “fix the two failing tests”.`
  Each UserPromptSubmit reminder proposes a wording shape, taken in turn per session (only
  the shape position is stored), so two suggestions in a row never read alike. Shapes are
  written for Chinese, Japanese, Korean and English; other languages follow the English
  ones in their own words. Only the
  quoted prompt is copied; Chinese prompts get a short go-ahead (`接着写第三章，做吧`, also
  来吧 / 开始吧 / 动手吧).
- The earlier `Next prompt:` / `下一步建议：` lines are still recognized. A closing offer
  whose arrow was dropped (`顺手的话，可以「…」。`) or that ends the last paragraph still
  counts; quotes in ordinary sentences or dialogue do not.
- A question mark at the end of a story or blurb no longer blocks the copy when the reply
  ends with a suggestion; explicit choices ("你想用哪个？", "Which branch…?") still do.
- `$nextprompt-status` shows local counts: how many replies suggested something and how many
  suggestions were sent as is, sent with more words, or not used, matched against the next
  prompt in the same session. Only counts and short one-way hashes are stored (`.stats.json`),
  never text. `setup --stats off` turns this off and deletes the counts; `--stats reset`
  clears them.
- No need to re-trust the hooks: the hook commands are unchanged.

## 0.1.13 — 2026-10-04

- Hosts whose default `python3` is older than 3.9 (Ubuntu 20.04, RHEL 8, openSUSE Leap 15)
  now work when a newer Python is installed next to it: the hook command, Doctor and
  `scripts/install.sh` also try `python3.15` down to `python3.9`, after `python`, `python3`
  and `py -3`.
- `scripts/install.sh` no longer stops at the distribution's default `python3` package when
  it is too old: it tries the versioned packages newest first (`python3.13` … `python3.9`
  with apt, `python3.13` … `python39` with dnf/yum, `python313` … `python39` with zypper).
- When no Python 3.9+ can be installed, the installer names the old Python it found and
  how to install a newer one, instead of suggesting to open a new terminal.
- The six skills tell Codex to use a `python3.X` command when `python` and `python3` are
  older than 3.9.
- Re-trust the hooks in `/hooks` after updating: the hook commands changed (versioned
  `python3.X` fallbacks).

## 0.1.12 — 2026-10-04

- Add `scripts/install.sh` for macOS / Linux. Like the Windows installer it registers
  the plugin, runs the doctor, asks about clipboard copy (or takes `--auto-copy on|off`)
  and ends with a bilingual usage report, so instructions show right after installation
  instead of only at the first trusted Codex session.
- Python: every entry point accepts Python 3.9+ through `python`, `python3` or the Windows
  `py -3` launcher. The hook command and Doctor gained the `py -3` fallback, and the Windows
  installer now accepts 3.9 (it required 3.10) and finds a py-launcher-only Python.
- When Python 3.9+ is missing, the installers install it: Windows through `winget`, or the
  official python.org installer after checking its Python Software Foundation signature
  when `winget` is unavailable; macOS through Homebrew or Apple's Command Line Tools;
  Linux through the system package manager.
- Both installers end with a bilingual (中文 / English) report: restart Codex, trust the
  Hooks, how suggestions look, how to turn off notifications and how to pause suggestions.
- Installers show the recommended settings (auto-copy and desktop notifications both on)
  and ask whether to keep them. Enter or Y keeps them; N asks for two letters, copy then
  notifications (`yn`, `ny`, `nn`, `yy`). The report that follows shows both saved values.
  New `-Notify on|off` / `--notify on|off` flags skip the question like `-AutoCopy`.
- CI runs Python 3.9 to 3.14 on the self-hosted Linux runner.
- Re-trust the hooks in `/hooks` after updating: the hook commands changed (new `py -3`
  fallback).

## 0.1.11 — 2026-10-04

- Stop the question loop: when a reply ends by asking the user something (a question
  mark, or asking them to choose, confirm or provide something), nothing is copied and
  the fallback model does not run. The instruction now tells the Codex model to omit the
  line in that case.
- Prompts that hand the decision back to the assistant ("下一步该做什么任务", "what should
  I do next", a bare "继续") are no longer copied or generated.
- Both the inline instruction and the fallback model now fix the user's typos instead
  of copying them into the suggestion.

## 0.1.10 — 2026-10-04

- On the first trusted SessionStart, display a one-time installation and usage report
  through the official Hook `systemMessage` field, while preserving the inline
  instruction through `additionalContext`. The report states the saved clipboard
  and notification settings, explains manual review/paste/send, and shows how to
  turn off notifications without disabling a Hook.
- The Windows installer report now explicitly mentions default-on notifications
  and how to turn them off. Installation still does not grant Hook trust.

## 0.1.9 — 2026-10-04

- Every Codex reply now ends with a next-step line by default. Its label and suggestion
  follow the language the user writes in (`Next prompt: …`, `下一步建议：…`,
  `次のプロンプト：…`, `다음 프롬프트: …` and the other supported languages; English label
  for any other language), and the text after the colon is copied to
  the clipboard exactly as shown, with no separate model request. A SessionStart Hook
  (also after compaction) gives the instruction and a new UserPromptSubmit Hook repeats a
  one-line reminder each turn. Lines that look like they contain a secret, contain
  control characters or exceed 500 characters are not copied.
- Replies without the line fall back to the lightweight model, as before.
  `setup --source model` restores the previous behavior (no line in replies).
- Re-trust the hooks in `/hooks` after updating: two hook events are new.

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
