# NextPrompt

NextPrompt adds lightweight AI-generated next-step suggestions to Codex after each completed turn.
**Codex-Prompty** is the repository/package name; **NextPrompt** is the plugin and skill name.
Version: **0.1.0**. Runtime: Python 3.10+, standard library only.

```text
Codex:
Implemented the authentication fix. Targeted tests pass.
Next → Run the full regression suite and review the final diff.
✓ Copied to clipboard
```

Codex's actual TUI adds its own `↳ Hook ·` prefix and indentation. The example shows
NextPrompt's text, not a custom component. Paste with Ctrl+V (Cmd+V on macOS), review,
then press Enter yourself. **NextPrompt never submits or executes the suggestion.**

## What is NextPrompt? Why?

An autocomplete layer for the natural next instruction after a coding task. It uses
recent conversation, rather than starting another project investigation. It produces
one short suggestion or nothing when the response is invalid or unhelpful.

## Features

- Root `Stop` hook only; no `SubagentStop` suggestions.
- Last 5 visible user/assistant messages, 2500 characters per message, 8000 total.
- Common credential redaction before clipping or inference.
- Account model discovery, conservative lightweight fallback, lowest supported reasoning.
- Explicit clipboard opt-in; display only and unavailable-clipboard fallback.
- Windows, WSL, macOS, Wayland and X11 clipboard adapters; optional OSC 52.
- No automatic execution, repository scan, transcript database or NextPrompt telemetry.
- Setup, status, enable, disable, manual suggestion and doctor skills.
- Fail-open errors, 15-second inference deadline and recursion protection.

## Compatibility and verified interfaces

Verified on **2026-10-03**, with **codex-cli 0.159.0-alpha.3**. Inference requires
the verified isolation flags introduced in this CLI generation; older versions are
skipped safely. Future versions should be checked with Doctor and the integration suite.

The current implementation needs the official **legacy plugin manifest** at
`.codex-plugin/plugin.json`. Although current documentation describes portable root
`plugin.json` hooks, the inspected source skips hook loading for that manifest format,
and a real CLI test confirmed no hook ran. The legacy format successfully ran Stop.
See [research findings](docs/RESEARCH.md) for sources and differences.

`systemMessage` is the official user-visible Hook output. It is displayed as a Hook
warning, outside the assistant's answer. No supported plugin copy-button or composer
ghost-text injection API was found. An experimental `thread/prediction/request`
app-server API exists, but does not let this plugin insert text into the existing TUI.
V1 does not patch Codex or install fake buttons.

## Installation

Ensure `codex --version` works and **`python --version` reports Python 3.10 or newer**.
The hook uses `python` on PATH on every platform. On Linux installations with only
`python3`, make a user-managed Python command available or change the hook command
to `python3` before installation. NextPrompt never installs system software.

For a private checkout at **Jineggegg/Codex-Prompty**, authenticate as its owner
before cloning. The commands below require that the private repository has been
created and populated. The plugin bundles all six skills; no package publication
or pip installation is needed.

```sh
gh auth login
gh repo clone Jineggegg/Codex-Prompty
cd Codex-Prompty
python scripts/doctor.py --probe
codex plugin marketplace add .
codex plugin add nextprompt@codex-prompty
```

The probe uses a synthetic conversation and may consume model quota. It returns a
nonzero exit status on an unavailable CLI, missing authentication, inference failure
or invalid suggestion. A missing desktop clipboard is allowed for display-only use.
If authentication fails, run **`codex login` on your local machine** and retry the
probe. Login status and model catalog entries alone are not proof of working inference.

Alternatively, register any existing checkout by its absolute path:

```sh
codex plugin marketplace add /absolute/path/to/Codex-Prompty
codex plugin add nextprompt@codex-prompty
```

These exact CLI commands were tested in an isolated Codex home. No pip installation
is needed to use the plugin. Restart Codex, then open **`/hooks` and review/trust the
NextPrompt hook**. Installing a plugin does not automatically trust its executable
hooks. Do not bypass trust review for normal use.

For private repository access, cloning first and registering the local path avoids
relying on how Codex forwards GitHub authentication to remote marketplace fetches.
See [local test checklist](docs/LOCAL_TEST.md) for a Chinese quick start and clipboard
checks. Source delivery is intended to remain private until the owner chooses to
make it public.

## First-time setup

The tested CLI install is non-interactive and has no generic Yes/No setup callback.
Until you configure clipboard behavior, NextPrompt shows this once, without inference:

```text
NextPrompt is installed.
Recommended:
Enable automatic clipboard copy.
Run:
$nextprompt-setup
```

Invoke **`$nextprompt-setup`** in Codex or say **“Configure NextPrompt.”** It asks:

```text
NextPrompt Setup
Automatically copy suggested next prompts to your clipboard?
Recommended: Yes
1. Yes — automatically copy suggestions
2. No  — display suggestions only
```

Only an explicit Yes enables copying. An absent answer or default recommendation
does not count as consent. You can also configure explicitly from the checkout:

```sh
python scripts/nextprompt.py setup --auto-copy on
# Or display only:
python scripts/nextprompt.py setup --auto-copy off
```

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

Manual `$nextprompt` uses only visible conversation supplied by the skill on stdin;
it does not search session directories. Hook mode reads only the supplied transcript
path. Management/manual skill turns may also receive a normal Stop suggestion;
use `trigger_mode: "manual"` if you only want explicit invocation.

## How it works

```text
Root Stop → re-entry/config guards → supplied transcript tail
          → visible prose → redact → last five → strict context limits
          → discover lightweight model → isolated, ephemeral codex exec
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
format uses `$CODEX_HOME/plugins/data/nextprompt-codex-prompty/config.json`
(`CODEX_HOME` defaults to `~/.codex`). A different marketplace can set
`NEXTPROMPT_MARKETPLACE` or pass `--data-dir /official/plugin/data` before the CLI
subcommand. The fixed marketplace name shipped here is `codex-prompty`.

Defaults:

```json
{
  "version": 1,
  "enabled": true,
  "trigger_mode": "every_turn",
  "clipboard": {"auto_copy": null, "osc52_fallback": false},
  "context": {
    "last_messages": 5,
    "max_chars_per_message": 2500,
    "max_total_chars": 8000
  },
  "model": {"name": "gpt-5.6-luna", "reasoning": "minimal", "timeout_seconds": 15},
  "suggestion": {"max_words": 20, "max_chars": 240},
  "privacy": {"redact_secrets": true}
}
```

`auto_copy: null` means setup pending; `false` means display only. These context,
word and character limits are hard V1 ceilings; they can be decreased. Invalid
configurations skip the hook without showing a traceback. Writes use a short
exclusive lock, unique temporary file, fsync and atomic replacement. A leftover
`.config.lock` after an interrupted settings update can be removed once no settings
operation is active. No suggestion files, transcript caches or usage profiles exist.
Only empty setup/error marker files are retained. Repeated model errors are shown
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
from NextPrompt. Clipboard contents can be read by other local applications, which
is why Auto Copy requires explicit consent. See [SECURITY.md](SECURITY.md).

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
model is a user choice. Failed inference skips instead of silently changing tiers.
`minimal` maps to `low` for the currently listed Luna models; high reasoning is
never selected by V1.

Authentication remains owned by Codex, through the existing `CODEX_HOME` and
runtime credential routing. NextPrompt neither reads nor copies OAuth tokens,
refresh tokens or credential files, and does not require `OPENAI_API_KEY` by default.
The isolated exec deliberately ignores user config, so custom model-provider
profiles are not supported by V1's default provider. Future providers can implement
the `SuggestionProvider.generate(context) -> str` interface independently.

Observed here: `codex login status` said **Logged in using ChatGPT**, and catalog
discovery listed Luna. A real child inference returned **401 / invalid authentication
token**. Therefore ChatGPT entitlement/quota reuse could not be validated. Real CLI
integration instead used a loopback simulated model service; that verifies plumbing,
not model quality, remote access or billing.

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

- No output: check setup, enabled/trigger settings, hook trust and transcript support.
- Model unavailable: run `codex login status` and the inference probe; reauthenticate
  using Codex's own login flow if required. No automatic login is attempted.
- No clipboard backend: use display only, or install your preferred clipboard tool
  yourself. In headless environments display only is the dependable default.
- Plugin edits not reflected: remove/add the installed plugin to refresh its cached
  bundle, then review changed hook trust again.
- `python` missing: verify the interpreter command in `hooks/hooks.json` before install.
- Malformed config: repair/delete only NextPrompt's own config, then run setup.

## Disable, uninstall and delete local config

```sh
python scripts/nextprompt.py disable
# Or $nextprompt-disable in Codex.
codex plugin remove nextprompt@codex-prompty
codex plugin marketplace remove codex-prompty
```

Removal commands were checked against the current CLI. Plugin removal deletes the
cached plugin bundle; config can remain. To remove local settings, delete only
`$CODEX_HOME/plugins/data/nextprompt-codex-prompty` (or the actual `PLUGIN_DATA`
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
setup consent, fail-open behavior, disabled mode and re-entry. Opt-in integration
tests install/remove the plugin with real CLI commands, exercise actual inference
arguments and root Stop, verify one suggestion and no recursive task, and inject a
model failure. Test hooks use trust bypass only inside a disposable, vetted fixture.
The loopback service never receives real credentials and stores only synthetic
requests in test memory. CI runs lint and unit tests on Ubuntu, Windows and macOS.
See [validation report](docs/VALIDATION.md) for the executed results and limitations.

## Security

Report concerns through the process in [SECURITY.md](SECURITY.md). All shipped test
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

See [CONTRIBUTING.md](CONTRIBUTING.md). Keep extensions small, privacy-conscious and
compatible with verified official APIs. Use feature branches and review changes
before release. Versions follow Semantic Versioning.

## License

[MIT](LICENSE).
