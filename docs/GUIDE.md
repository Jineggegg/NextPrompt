# NextPrompt — complete guide

NextPrompt adds lightweight AI-generated next-step suggestions to Codex after each completed turn.
NextPrompt is the product, repository, package, plugin and marketplace name.
Version: **0.1.11**. Runtime: Python 3.9+, standard library only.

**下一句，已经准备好了。** 每轮完成后，NextPrompt 为你准备一句简短的下一步提示词。
安装时选择 **Y**，有效建议就会**自动复制到剪贴板**：按 **Ctrl+V**（macOS：**Cmd+V**），
检查后发送，省去手动选中和复制。

- **通常几秒就绪。** 独立轻量会话生成建议；15 轮真实模型测试中，11 轮耗时
  **3–5 秒**，平均 **4.37 秒**。完整样本范围为 3.06–6.56 秒，实际速度随模型和网络变化。
- **为低 token 开销而设计。** 只使用最近 5 条可见消息（最多 8000 字符），默认轻量模型
  配合 `low` 思考，只生成一句建议（最多 20 个词、240 字符）。独立请求仍会消耗额度；
  完整输入、输出与思考 token 尚未计量，不能据此保证“几乎零消耗”。
- **自动加入剪贴板，直接粘贴继续。** 安装选择 Y 后会保存偏好，并在结束报告中确认已开启。
  默认开启（直接回车即可），建议就绪时还会弹出系统通知；选择 N 则仅显示建议，可随时通过 `$nextprompt-setup` 切换。

**Your next instruction, ready to paste.** Opt into automatic clipboard copy during installation,
then paste, review and send. Most of our 15 measured synthetic turns took **3–5 seconds**
(mean **4.37s**). Short context and a lightweight model at `low` keep the request focused;
actual token usage has not been measured. See the [measurement details](VALIDATION.md#measured-latency-and-token-scope).

```text
Codex:
Implemented the authentication fix. Targeted tests pass.
Next prompt:
Run the full regression suite and review the final diff.
```

Codex's actual TUI adds its own `↳ Hook ·` prefix and indentation. The example shows
NextPrompt's display-only text, not a custom component. Copy and review the
suggestion before using it. With optional Auto Copy enabled, paste with Ctrl+V
(Cmd+V on macOS), review, then press Enter yourself.
**NextPrompt never submits or executes the suggestion.**

## What is NextPrompt? Why?

An autocomplete layer for the natural next instruction after a coding task. It uses
recent conversation, rather than starting another project investigation. It produces
one short suggestion or nothing when the response is invalid or unhelpful.

## Features

- By default the root Codex model ends each reply with a `Next prompt:` (Chinese:
  `下一步建议：`) line, requested through SessionStart and UserPromptSubmit hooks; the root
  `Stop` hook copies the text after the colon unchanged. Replies without the line, or
  `--source model`, use the separate lightweight request below. No `SubagentStop` suggestions.
- Last 5 visible user/assistant messages, 2500 characters per message, 8000 total.
- Common credential redaction before clipping or inference.
- Account model discovery, conservative lightweight runtime fallback, `low` reasoning by default.
- Automatically copy valid suggestions to the clipboard (on by default) and show a desktop
  notification when each one is ready; display-only mode and manual-copy fallback are available.
- Windows, WSL, macOS, Wayland and X11 clipboard adapters; optional OSC 52.
- No automatic execution, repository scan, transcript database or NextPrompt telemetry.
- Setup, status, enable, disable, manual suggestion and doctor skills.
- Fail-open errors, 15-second inference deadline and recursion protection.
- Multilingual: suggestions follow the user's language; labels follow the latest user
  message or a configured `language` (en, zh, zh-TW, ja, ko, es, fr, de, pt, ru).
  Length limits, generic-reply filters and completed-work guards understand Chinese,
  Japanese, Korean and other scripts, not only English.
- A 12-hour capability cache skips repeated Codex checks on later turns.

## Compatibility and verified interfaces

Verified on **2026-10-03**, with **codex-cli 0.159.0-alpha.3**. Inference requires
the verified isolation flags introduced in this CLI generation; older versions are
skipped safely. Future versions should be checked with Doctor and the integration suite.

The current implementation needs the official **legacy plugin manifest** at
`.codex-plugin/plugin.json`. Although current documentation describes portable root
`plugin.json` hooks, the inspected source skips hook loading for that manifest format,
and a real CLI test confirmed no hook ran. The legacy format successfully ran Stop.
See [research findings](RESEARCH.md) for sources and differences.

`systemMessage` is the official user-visible Hook output. It is displayed as a Hook
warning, outside the assistant's answer. No supported plugin copy-button or composer
ghost-text injection API was found. An experimental `thread/prediction/request`
app-server API exists, but does not let this plugin insert text into the existing TUI.
V1 does not patch Codex or install fake buttons.

## Installation

The hook runs `python` on PATH and falls back to `python3`, then to the Windows `py -3`
launcher, when the previous one is missing or older than Python 3.9, so stock macOS
(Python 3.9), Linux and py-launcher-only Windows installs need no extra setup. The runtime
and Hook never install software. Only the explicitly invoked installers do, and only when
Python 3.9+ is missing: on Windows, `winget` installs Python 3.12 for the current user
(without `winget`, the official python.org installer is downloaded and run only if its
Authenticode signature is valid and from the Python Software Foundation); on macOS,
Homebrew or Apple's Command Line Tools; on Linux, the system package manager (with sudo).

Clone **Jineggegg/NextPrompt** with Git. The plugin bundles all six skills; no
package publication or pip installation is needed. Commands in this guide use
`python`; on macOS/Linux use `python3` if `python` is unavailable.

Windows quick install:

```powershell
git clone https://github.com/Jineggegg/NextPrompt.git
Set-Location NextPrompt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

The script verifies `codex`, installs Python 3.12 through the official `winget`
source when required, refreshes the current process PATH, registers the marketplace,
installs the plugin, runs Doctor and asks Y/N about automatic clipboard copy.
Y or an empty answer enables automatic copy (default); N selects display only. The choice
is saved and clearly reported at completion; other existing settings are preserved.
For unattended installation, pass `-AutoCopy on` or `-AutoCopy off` explicitly.
Add `-Probe` to perform a synthetic inference
test; it may consume model quota. The execution-policy override applies only to this
PowerShell process and does not change the user's system policy. If `winget` is
unavailable, it downloads the official python.org installer and runs it per user only
after verifying its Python Software Foundation signature; it never requests elevation.

macOS / Linux install:

```sh
git clone https://github.com/Jineggegg/NextPrompt.git
cd NextPrompt
sh scripts/install.sh            # add --auto-copy on|off for unattended use, --probe to test inference
```

The script registers the plugin, runs the doctor, saves the clipboard choice and prints
the same restart, `/hooks` trust and usage steps as the Windows installer.

Manual install (Codex prints no NextPrompt instructions; the one-time report appears at
the first trusted session):

```sh
git clone https://github.com/Jineggegg/NextPrompt.git
cd NextPrompt
python scripts/doctor.py --probe
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
```

The probe uses a synthetic conversation and may consume model quota. It returns a
nonzero exit status on an unavailable CLI, missing authentication, inference failure
or invalid suggestion. A missing desktop clipboard is allowed for display-only use.
If authentication fails, run **`codex login` on your local machine** and retry the
probe. Login status and model catalog entries alone are not proof of working inference.

Alternatively, register any existing checkout by its absolute path:

```sh
codex plugin marketplace add /absolute/path/to/NextPrompt
codex plugin add nextprompt@nextprompt
```

These CLI commands were tested in an isolated Codex home. No pip installation
is needed to use the plugin. Restart Codex, then open **`/hooks` and review/trust the
NextPrompt hook**. Installing a plugin does not automatically trust its executable
hooks. Do not bypass trust review for normal use.

See [local test checklist](LOCAL_TEST.md) for a Chinese quick start and clipboard
checks.

## After installation: no setup required for suggestions

Setup is not a prerequisite and is not specific to the repository owner. New
installations **copy each suggestion automatically and show a desktop notification**.
The Windows installer asks for the clipboard preference and updates only that
chosen setting; manual installs preserve existing settings. After loading the plugin
and trusting its Hook,
complete a normal conversation turn to see a useful next-prompt suggestion.

After Doctor passes, the Windows installer asks:

```text
NextPrompt clipboard preference
Automatically copy suggested next prompts to your clipboard?
Y = automatic copy (default); N = display only.
Other local applications may read clipboard contents.
Choose Y or N [Y]:
```

If you enter **Y** or press Enter, the completion guide includes:

```text
NextPrompt installed successfully.
Automatic clipboard copy: ON. New suggestions will be copied automatically.
A desktop notification shows each suggestion when it is ready to paste.
Your clipboard choice has been saved. Other existing settings are preserved.
No additional setup is required.

Finish in Codex:
1. Fully quit and reopen Codex to load the plugin and refreshed PATH.
2. Open /hooks, review the NextPrompt SessionStart, UserPromptSubmit and Stop hooks, and trust them.
   Installation does not grant hook trust or bypass your approval.
3. Complete a normal conversation turn. A useful suggestion appears as:
   Next prompt:
   Run the full regression suite and review the final diff.
   (Example only; suggestions depend on the conversation.)

Optional: run $nextprompt-setup to change clipboard copy or other settings.
Help: run $nextprompt-status or $nextprompt-doctor.
If /hooks is unavailable, use a supported Codex client/CLI; automatic suggestions are not verified until the hook loads and is trusted.
```

If you enter **N**, the mode line instead reads:

```text
Automatic clipboard copy: OFF. Suggestions will be displayed only.
```

An unavailable interactive terminal stops with guidance to use `-AutoCopy on|off`.
If saving the preference fails, no successful
installation report is printed. Enabling copy does not copy anything at installation:
copying occurs only for valid suggestions after completed turns, once the Hook loads
and is trusted. A missing clipboard backend is reported by the suggestion output;
the suggestion remains available for manual copy.

The same restart and Hook review steps apply to direct `codex plugin add` installs;
those commands are supplied by Codex and cannot print this installer's custom guide.
Installing just the skills does not register the automatic Stop Hook. Use the full
plugin install described above for automatic suggestions. We never grant trust on
your behalf. If no suggestion appears, run `$nextprompt-doctor` and check `/hooks`.
Generic or repeated suggestions may be discarded; output is not guaranteed every turn.

## Optional setup: clipboard copy or custom settings

Only if you want to turn clipboard copy or notifications off, or change other settings, invoke
**`$nextprompt-setup`** in Codex or say **“Configure NextPrompt.”** A general setup asks:

```text
NextPrompt Setup
Automatically copy suggested next prompts to your clipboard?
Default: Yes
1. Yes — automatically copy suggestions
2. No  — display suggestions only
```

An empty answer keeps the default (Yes). Requests
to change only a model or another setting preserve clipboard behavior and do not
ask an unrelated clipboard question. You can also configure explicitly from the checkout:

```sh
python scripts/nextprompt.py setup --auto-copy on
# Or display only:
python scripts/nextprompt.py setup --auto-copy off
# Turn desktop notifications off (or back on):
python scripts/nextprompt.py setup --notify off
```

On macOS the notification comes from AppleScript (Script Editor); allow notifications
for it in System Settings → Notifications if none appear. Windows uses a standard toast
and Linux desktops use `notify-send` when installed. Headless/SSH sessions skip it.

In the TUI's `$` skill picker, plugin skill names may be displayed with the
`nextprompt:` namespace. Select the installed skill if the bare name is ambiguous.
There is no separately implemented alias API. Natural-language descriptions also
route to these skills.

## Usage and modes

| Skill | Natural request |
| --- | --- |
| `$nextprompt-setup` | Configure NextPrompt; turn NextPrompt clipboard copy off |
| `$nextprompt-status` | Show NextPrompt status |
| `$nextprompt-enable` | Enable NextPrompt |
| `$nextprompt-disable` | Disable NextPrompt |
| `$nextprompt-doctor` | Diagnose NextPrompt |
| `$nextprompt` | Suggest my next prompt |

Auto Copy:

```text
Next → Run the full regression suite and review the final diff.
✓ Copied to clipboard
```

The clipboard contains only `Run the full regression suite and review the final diff.`
If copying fails:

```text
Next → Run the full regression suite and review the final diff.
Clipboard unavailable — copy the prompt above manually.
```

Display Only:

```text
Next prompt:
Run the full regression suite and review the final diff.
```

Labels follow the language of your latest message. A Chinese conversation shows:

```text
下一句 → 运行完整回归测试，检查最终改动。
✓ 已复制到剪贴板
```

Chinese (Simplified/Traditional), Japanese, Korean and Russian are recognized from
their scripts; other conversations use English labels unless you pin a language with
`setup --language en|zh|zh-TW|ja|ko|es|fr|de|pt|ru` (`auto` restores detection).
The suggestion itself is always written in the language of your latest message.

Manual `$nextprompt` uses only visible conversation supplied by the skill on stdin;
it does not search session directories. Hook mode reads only the supplied transcript
path. Management/manual skill turns may also receive a normal Stop suggestion;
use `trigger_mode: "manual"` if you only want explicit invocation.

## How it works

```text
Root Stop → re-entry/config guards → supplied transcript tail
          → visible prose → redact → last five → strict context limits
          → cached or fresh model discovery → isolated, ephemeral codex exec
          → sanitize/obvious-repeat checks → optional clipboard → Hook systemMessage
```

Only a bounded **2 MiB tail of one transcript** is read. The parser supports current
`response_item` messages and older `event_msg` messages, preferring canonical items
to avoid duplicates. It ignores tool calls/results, reasoning, images, metadata,
fenced code and common diff/log lines. Malformed records are skipped. A record larger
than the read window can be omitted. Transcript layout is not an official stable
interface; unsupported layouts or null paths produce no suggestion.

The 8000-character limit includes role labels and delimiters in the formatted
conversation. Older content is clipped first. Codex adds its own protocol and
environment information around this bounded conversation. The child runs from a
unique empty directory under plugin data, with a short fixed instruction file;
it does not run from or inspect the user's repository.

The child uses `--ephemeral`, `--ignore-user-config`, `--ignore-rules`, read-only
sandboxing, `web_search="disabled"`, and disabled shell, MCP plugins, apps, browser,
computer use, image generation and subagent features. User/project instruction
discovery is suppressed. `NEXTPROMPT_INTERNAL=1` plus `--disable hooks` and
`--disable plugins` protect against recursion. A future CLI may expose utility
tools that cannot all be disabled through public flags; the current lightweight
model integration verified absence of shell, web, MCP and patch tools. Read-only
is an additional boundary, not a claim of a universal tools-free CLI API.

After a successful suggestion, NextPrompt caches the verified Codex executable
fingerprint and model catalog in `codex-cache.json` under plugin data for 12 hours.
Later turns skip `codex exec --help`, `codex --version` and app-server discovery.
A Codex upgrade, a model setting change, a rejected model or Doctor refreshes it.
The cache never contains conversation text.

Stop is a completion checkpoint, before Codex applies the aggregate decisions of
other Stop hooks. If another plugin requests continuation, this hook cannot observe
that future decision. NextPrompt never requests continuation and skips subsequent
`stop_hook_active` runs; strict once-after-final-completion behavior is verified for
ordinary turns without a continuing Stop hook from another plugin.

The deadline includes capability checks, model discovery and inference; process
groups are terminated on timeout. Codex may perform transport retries within that
deadline. Clipboard processes share a separate 2-second budget. The Hook has a
20-second outer timeout. Success should be quick, but the 15-second deadline is
a limit, not a measured real-model latency guarantee.

## Clipboard support

| Platform | Implementation | Validation in this environment |
| --- | --- | --- |
| Windows 10/11 | PowerShell `Set-Clipboard`, then `clip.exe` | Supported by implementation; mock Unicode tests |
| WSL / WSL2 | Windows `clip.exe`, then PowerShell bridge | Supported by implementation; mock Unicode tests |
| macOS | `pbcopy` | Supported by implementation; mock Unicode tests |
| Linux Wayland | `wl-copy`, then X11 tools if present | Supported by implementation; mock Unicode tests |
| Linux X11 | `xclip`, then `xsel` | Supported by implementation; mock Unicode tests |
| SSH/headless Linux | Display; optional OSC 52 | Tested: no-backend detection and display fallback |

WSL/native `clip.exe` receives UTF-16LE; other tools receive UTF-8. PowerShell sets
its stdin decoding to UTF-8. English, Chinese, emoji and multiline payloads have
exact-byte mock tests. Desktop clipboard round trips still need real machines.
No Linux backend was present here, so no real clipboard was changed or read.

OSC 52 is **off by default**. With explicit `--osc52 on`, it requires a recognized
terminal, an attached TTY, a 4096-byte maximum, and no tmux/screen intermediary.
It is best effort and cannot confirm terminal acceptance; output says “copy
requested,” never “copied.” Turn it off if your terminal or host disallows it.
No backend is downloaded or installed. Concurrent sessions share the system
clipboard: the last completed copy wins.

## Configuration

Hook configuration lives in **`PLUGIN_DATA/config.json`**, outside the user's
repository. For skills/CLI without injected `PLUGIN_DATA`, this verified legacy
format uses `$CODEX_HOME/plugins/data/nextprompt-nextprompt/config.json`
(`CODEX_HOME` defaults to `~/.codex`). A different marketplace can set
`NEXTPROMPT_MARKETPLACE` or pass `--data-dir /official/plugin/data` before the CLI
subcommand. The fixed marketplace name shipped here is `nextprompt`.

Defaults:

```json
{
  "version": 1,
  "enabled": true,
  "trigger_mode": "every_turn",
  "language": "auto",
  "notify": true,
  "clipboard": {"auto_copy": true, "osc52_fallback": false},
  "context": {
    "last_messages": 5,
    "max_chars_per_message": 2500,
    "max_total_chars": 8000
  },
  "model": {"name": "gpt-5.6-luna", "reasoning": "low", "timeout_seconds": 15},
  "suggestion": {"max_words": 20, "max_chars": 240},
  "privacy": {"redact_secrets": true}
}
```

`auto_copy: true` (the default) copies each suggestion; `false` is display-only, and a
legacy `null` follows the default. `notify: true` (the default) shows a desktop
notification after copying. These context,
word and character limits are hard V1 ceilings; they can be decreased. Invalid
configurations skip the hook without showing a traceback. Writes use a short
exclusive lock, unique temporary file, fsync and atomic replacement. A leftover
`.config.lock` after an interrupted settings update can be removed once no settings
operation is active. No suggestion files, transcript caches or usage profiles exist.
Only empty error marker files and the capability cache (Codex fingerprint and model
catalog, no conversation) are retained; older setup markers are ignored. Repeated model errors are shown
at most once per category per hour; unexpected errors are silent.

`every_turn` is the automatic default. `manual` disables automatic generation.
`code_change_only` is reserved and also skips automatic generation in V1; there is
no repository-based change detector. Re-enable with `setup --trigger-mode every_turn`.

## Privacy

By default NextPrompt:

- reads only the last 5 conversational messages for inference;
- applies strict context size limits;
- redacts common secrets before inference;
- does not store conversation transcripts;
- does not run its own remote backend;
- does not collect telemetry.

Redaction recognizes common OpenAI, Anthropic, GitHub, AWS and Stripe keys, Bearer
tokens, private-key blocks, JWT-like tokens and obvious password/token/API-key/secret
assignments. It is conservative but is not a proof that all sensitive information
was removed. Keep redaction enabled. Model output containing recognizable secrets
is discarded as well. No raw subprocess errors or conversation content are logged
by NextPrompt. Codex analytics/exporters are disabled for inference.

Redacted conversation is sent to **the model service used by the child Codex CLI**,
subject to that service's policies and account settings. The user-controlled Codex
installation, authentication store and parent session persistence remain separate
from NextPrompt. Clipboard contents can be read by other local applications; only the
suggestion text is copied, and Auto Copy can be turned off. See [SECURITY.md](../SECURITY.md).

## Models and quota

NextPrompt attempts to use the authenticated Codex environment where supported.
Model availability and quota behavior depend on the user's Codex account and
current OpenAI product behavior. **No claim of free ChatGPT inference is made.**

The provider uses official `model/list` to check catalog models and supported
reasoning efforts, then selects:

1. The configured model, when present and supporting low reasoning.
2. `gpt-5.6-luna`.
3. `gpt-6-luna`, `gpt-5.1-codex-mini`, or `gpt-5-codex-mini`, in that order.
4. Skip if no conservative lightweight candidate exists.

The catalog has no pricing field, and may fall back to Codex's bundled catalog:
a listed model is not proof of entitlement or current price. This allowlist is
an explicit V1 policy, not an assertion that it calculates the lowest cost model.
No large/default model is selected automatically. An explicitly configured larger
model is a user choice. If a catalog-listed model is explicitly rejected at inference
time (missing, unsupported or inaccessible), NextPrompt tries the next listed
lightweight candidate at `low`. Hidden models and candidates without `low` are skipped.
Each candidate gets at most one child execution and all attempts share the same
15-second deadline. Codex may retry HTTP requests within that child execution.
Authentication, quota, timeout, network and unknown errors stop immediately; they do
not trigger model hopping. No expensive tier is selected automatically.
Existing explicit `none`/`minimal` settings remain respected for the configured
model; new settings default to `low`. High reasoning is never selected by V1.

Suggestions are limited to one sentence of at most 20 words and 240 characters.
For scripts written without spaces, about two Chinese/Japanese characters (or four
Thai-like letters) count as one word, so a Chinese suggestion is at most about 40
characters.

The suggestion style is inspired by Claude-style prompt continuation: predict what
the user would naturally type next, in their language, as one short specific clause.
It is not a copy of Claude's private system prompt and does not call Claude. Suggestions
preserve stated approval/read-only boundaries, avoid completed work and do not invent
features. When the task is finished, silence is preferable to an unnecessary suggestion.

Authentication remains owned by Codex, through the existing `CODEX_HOME` and
runtime credential routing. NextPrompt neither reads nor copies OAuth tokens,
refresh tokens or credential files, and does not require `OPENAI_API_KEY` by default.
The isolated exec deliberately ignores user config, so custom model-provider
profiles are not supported by V1's default provider. Future providers can implement
the `SuggestionProvider.generate(context) -> str` interface independently.

Authenticated inference was verified in the later 15-round synthetic test using
gpt-5.6-luna / low. Earlier authentication failures are retained as historical
evidence in [VALIDATION.md](VALIDATION.md); working access still depends on each
user's own Codex login and model entitlement. Local-service integration tests
verify plugin behavior without claiming to measure remote quality or billing.

## Troubleshooting and Doctor

```sh
python scripts/doctor.py
# Optional synthetic inference; may consume account quota:
python scripts/doctor.py --probe
python scripts/nextprompt.py status
```

Doctor distinguishes login-status checks, catalog discovery, actual inference probes
and clipboard detection. It never prints credentials or full home paths. It cannot
prove hook trust from metadata; inspect `/hooks` yourself.
Exit code 0 means the checks requested by that command passed; code 1 means a required
check failed. Only `--probe` validates an actual model response. Authentication and
quota failures are summarized as safe categories, without the original CLI error.

- No output: check enabled/trigger settings, hook trust and transcript support; setup is optional.
- `hook: Stop Failed`: run Doctor and check the `Hook Python` row; the hook needs
  `python`, `python3` or (Windows) `py -3` with 3.9+ on PATH (the macOS-bundled `python3` qualifies).
- Model unavailable: run `codex login status` and the inference probe; reauthenticate
  using Codex's own login flow if required. No automatic login is attempted.
- No clipboard backend: use display only, or install your preferred clipboard tool
  yourself. In headless environments display only is the dependable default.
- Plugin edits not reflected: remove/add the installed plugin to refresh its cached
  bundle, then review changed hook trust again.
- `python` missing on Windows: rerun `scripts/install.ps1`; on other platforms,
  install Python 3.9+ so that `python3` or `python` is on PATH.
- Malformed config: repair/delete only NextPrompt's own config, then run setup.

## Disable, uninstall and delete local config

```sh
python scripts/nextprompt.py disable
# Or $nextprompt-disable in Codex.
codex plugin remove nextprompt@nextprompt
codex plugin marketplace remove nextprompt
```

Removal commands were checked against the current CLI. Plugin removal deletes the
cached plugin bundle; config can remain. To remove local settings, delete only
`$CODEX_HOME/plugins/data/nextprompt-nextprompt` (or the actual `PLUGIN_DATA`
for this plugin). Do not remove `CODEX_HOME`, Git directories or your repository.
Disabling makes Stop return after reading the enabled flag: no transcript reads,
model calls, marker updates or clipboard activity.

## Architecture

```text
NextPrompt Core
├── ConfigStore             official data location, atomic config
├── ConversationAdapter     Codex transcript → visible messages
├── SuggestionProvider      Codex model/list + ephemeral exec
├── ClipboardAdapter        platform commands / optional OSC 52
└── OutputAdapter           official Hook JSON / terminal / future GhostText
```

Small modules keep conversation, inference, output and clipboard concerns separate.
`GhostTextOutputAdapter` is a deliberately unavailable placeholder. Other agents or
providers can replace adapters without changing the prediction engine. No plugin
code forks or modifies Codex.

## Development and testing

```sh
python -m pip install -e '.[dev]'
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
# POSIX, Codex 0.159+ installed; local simulated inference only:
NEXTPROMPT_RUN_CLI_INTEGRATION=1 python -m pytest -q
```

Unit tests cover parsing, size limits, redaction/provider boundaries, sanitization,
completed-work guards, config concurrency, clipboard backend order/Unicode, explicit
setup choices, notifications, fail-open behavior, disabled mode and re-entry. Opt-in integration
tests install/remove the plugin with real CLI commands, exercise actual inference
arguments and root Stop, verify one suggestion and no recursive task, and inject a
model failure. Test hooks use trust bypass only inside a disposable, vetted fixture.
The loopback service never receives real credentials and stores only synthetic
requests in test memory. CI runs lint and unit tests on Ubuntu, Windows and macOS.
See [validation report](VALIDATION.md) for the executed results and limitations.

## Security

Report concerns through the process in [SECURITY.md](../SECURITY.md). All shipped test
tokens are obviously fake. No source credential, auth file or transcript should be
committed. MIT licensing does not imply a security or availability guarantee.

## Roadmap

- Verify real desktop clipboard round trips and authenticated subscription inference.
- Revalidate portable hooks when Codex's runtime supports them.
- Add provider adapters for API and local inference.
- Add other conversation adapters (Claude Code, Gemini CLI, Cursor, OpenCode, Studio).
- Implement ghost text only when an official plugin composer contract exists.

Multiple suggestions and personalization are future work. Any long-term preference
storage would require explicit opt-in; V1 does not create a behavioral database.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md). Keep extensions small, privacy-conscious and
compatible with verified official APIs. Use feature branches and review changes
before release. Versions follow Semantic Versioning.

## License

[MIT](../LICENSE).
