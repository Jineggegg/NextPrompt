# Validation

## v0.1.9 — 2026-10-04, next-step line in every reply by default

- Codex source (openai/codex at the time of writing): plugin hooks load like any other
  hook; plain stdout from SessionStart and UserPromptSubmit is recorded as a developer
  message for the root model (`core/src/hook_runtime.rs`, `record_additional_contexts`),
  and SessionStart fires again after compaction. Stop input includes `last_assistant_message`.
- Real Codex CLI 0.160.0 with the local simulated model (`NEXTPROMPT_RUN_CLI_INTEGRATION=1`,
  7 passed): the root request carried both the SessionStart instruction and the
  UserPromptSubmit reminder; with a reply ending in `Next prompt: …` the Stop Hook made no
  suggestion request; replies without the line still made exactly one fallback request.
- Whether a real model writes the line on every turn was not measured here; the fallback
  covers replies that omit it.

## v0.1.8 — 2026-10-04, default auto-copy, notifications, slimmer requests

- Real child request captured from Codex 0.160.0 and 0.159.0: 14,285 → 8,768 bytes.
  Remaining tools: code-mode `exec`/`wait` only (forced by the model catalog; with the
  shell disabled they have no file or network access). `request_user_input` removed.
- Local Codex startup plus request (simulated model): 0.20–0.43 s; the rest of the
  user-visible delay is remote model time, which was not re-measured.
- A Stop-time probe over three real Codex turns showed the transcript already contains
  the latest user message and reply when the Hook runs.
- Notifications are unit-tested per platform (argument/environment passing, detached
  launch, silent failure); a real desktop notification was not observed here.

## v0.1.7 — 2026-10-04, macOS-bundled Python 3.9

- User report on 0.1.6: first turn showed `hook: Stop Failed` and no suggestion.
- Reproduced with real Codex 0.160.0 on a host with no `python` and `python3` = 3.9:
  0.1.6 reported `hook: Stop Failed` and made no suggestion request (2/2 runs).
  0.1.7 completed the Hook and requested one suggestion (4/4 runs).
- Full suite on Python 3.9, which 0.1.6 never tested: only the version guard failed;
  all other engine tests passed, so the minimum was lowered to 3.9.

## v0.1.6 — 2026-10-04, pre-release review and full regression

- Linux, Python 3.10 / 3.11 / 3.12 / 3.13 with real Codex CLI **0.160.0** and
  `NEXTPROMPT_RUN_CLI_INTEGRATION=1`: **303 passed, 21 skipped** on each version
  (the skips are Windows-only installer cases). Integration and hook suites also
  passed with Codex **0.159.0**. Ruff lint/format passed.
- Capability cache against real Codex 0.160.0 and the local simulated model: NextPrompt's
  own overhead per turn fell from 0.77–1.64 s (cold) to 0.24–0.32 s (cached). Remote
  model latency is added on top and was not re-measured.
- GitHub Actions on Ubuntu, macOS and Windows with Python 3.10 and 3.12: all green;
  Windows ran the 21 installer cases and the new `cmd.exe` hook-command cases.
- Real Codex 0.160.0 confirmed that the Hook's injected `PLUGIN_DATA` equals the
  data directory used by the skills/CLI, and that a real rollout parses into only
  the visible user/assistant messages.
- Before the fix, a real Codex Stop on a host with `python3` but no `python`
  (stock macOS/Linux) reported `hook: Stop Failed` and made no suggestion request.
  With the `python` → `python3` fallback the same run completed and requested one
  suggestion.
- Not verified here: real desktop clipboard round trips and authenticated remote
  inference; earlier Windows results for those remain the latest evidence.

## v0.1.5 — 2026-10-04, unified NextPrompt identity

- Windows full suite: **247 passed, 7 skipped**; lint/format and all six skill
  validations passed. Marketplace, package, commands and data paths now use NextPrompt.
- Actual Windows installation of `nextprompt@nextprompt` **0.1.5** passed Doctor
  and an authenticated synthetic inference probe. The previous display-only preference
  was retained; no real clipboard contents were read or copied.
- In the independent WSL environment, the new official install/remove case passed.
  The inference case timed out; even the unchanged Codex 0.160.0 `--version` command
  could not finish within a separate five-second probe. Both the Node launcher and
  packaged native binary showed this startup issue. The complete six-case WSL suite
  is **not claimed as passing** for this run. Production deadlines were preserved.
- Earlier 15-round timings remain the v0.1.2 sample, not a new speed measurement.

## v0.1.4 — 2026-10-04, clipboard choice at installation

- Full Windows suite: **247 passed, 7 skipped**. Ruff lint and format checks passed.
- Copied bundle in an independent Windows venv: all **21 installer cases passed**;
  all six skills validated in UTF-8 mode.
- The installer keeps the NextPrompt name and all six existing skill commands.
- Installer tests run real PowerShell with simulated prerequisite commands and
  persist the choice through the real configuration CLI into disposable directories.
  They cover Y/Yes, N/No, empty input, invalid input/retry, explicit unattended flags,
  unavailable interactive input, prerequisite failures and failed preference saving.
- Y saves `auto_copy: true` and the completion report states automatic copy is ON;
  N or empty input saves false and reports display only. Tests do not copy to the
  user's real clipboard, download Python or grant Hook trust.

## Measured latency and token scope

The existing **v0.1.2** benchmark generated 15 valid suggestions from a fictional
Chinese notes-app conversation using **gpt-5.6-luna / low**. Measurements cover the
Stop-handler pipeline, including context processing, model discovery and authenticated
child inference. They exclude the parent conversation and desktop rendering. Clipboard
copy was off. This is one recorded sample, not a new v0.1.4 benchmark or a speed guarantee.

- Mean: **4.372 seconds**; median: **4.19 seconds**.
- **11 of 15** rounds took 3–5 seconds; all rounds ranged from **3.06 to 6.56 seconds**.
- [Raw synthetic dialogue and timings](benchmarks/nextprompt-15-rounds.json).

Low-overhead design is supported by bounded recent context, short output, `low`
reasoning and no repository investigation in the suggestion child. The configured
limits are **5 visible messages / 8000 characters** and **20 words / 240 characters**;
these are not token counts. The benchmark did not record complete input, output or
reasoning usage, current pricing, or a comparison against the parent conversation.
Consequently, negligible token consumption and negligible cost are not established.
The separate request may consume account quota; actual use depends on context and model.

## v0.1.3 — 2026-10-04, setup-free display onboarding

- Independent Windows environment: **234 passed, 7 skipped**.
- Independent WSL environment with real Codex CLI/local-service integration enabled:
  **233 passed, 8 skipped**, including all six integration cases.
- The real Stop Hook now generates display-only suggestions from a fresh install
  with no config file; Unicode output and recursion isolation still pass.
- Fresh and legacy unset configs never access or copy to the clipboard. Explicit
  clipboard choices survive non-clipboard configuration changes and installation.
- Real Windows installer registered and installed version **0.1.3**. Doctor reported
  `defaults ready (display only)` and the installer displayed restart, `/hooks`
  review/trust, an example suggestion, optional setup and diagnostic instructions.
- A real account inference using the installed 0.1.3 CLI, synthetic conversation and
  fresh data directory returned a useful suggestion without running setup or creating
  `config.json`. It did not enable clipboard copying.
- Ruff lint/format checks and both changed skills' validation passed. The skill
  validator was run in UTF-8 mode on Windows for non-ASCII text.

Desktop Hook approval/restart remains a user action. These checks do not prove that
an already-open desktop chat has reloaded or trusted the updated Hook. Direct Codex
plugin commands cannot display the PowerShell script's custom completion guide;
their users must follow the matching README steps.

## v0.1.2 — 2026-10-03–04, independent Windows and WSL environments

**Status: PASS for automated checks, authenticated suggestions and isolated real CLI
Hook integration. Desktop Hook trust and clipboard consent remain user-controlled.**

```text
Windows: fresh Python 3.12.10 venv, copied plugin bundle
  pytest                         229 passed, 7 platform/opt-in skips (9.66s)
WSL: fresh Linux-local venv, copied plugin bundle, Codex CLI 0.160.0
  pytest with CLI integration    228 passed, 8 Windows-only skips (23.01s)
ruff check / format check        PASS — 42 repository Python files
Installed Windows plugin         0.1.2, enabled
PowerShell install -Probe        PASS — authenticated short suggestion
Synthetic multi-turn test        15/15 valid real generated suggestions
Selected model in all 15 turns   gpt-5.6-luna / low
Clipboard read or write          None
```

The synthetic dialogue concerns a fictional local notes app. Each stop event uses
only the latest five visible messages, generates through the authenticated Codex
child process, and renders a display-only suggestion. UTF-8 reports contain the
fictional user/assistant messages, exact suggestions, selected model and timings.
This validates that pipeline, not the desktop UI presentation or real clipboard.

Six opt-in cases use real Codex installation/exec/Stop Hook processes with a local
simulated Responses service and disposable CODEX_HOME, without real credentials.
They cover installation/removal, short no-tool ephemeral inference, runtime model
rejection followed by gpt-6-luna/low, English/Unicode Hook output, no recursion, and
root-task success after child authentication failure. Codex may retransmit the first
rejected HTTP request; the provider selects only one fallback candidate in that case.
Tests verify actual rollout files, excluding Codex's bundled example JSONL fixtures.

Eight Windows installer cases simulate existing/missing/old Python, a broken App
Execution Alias, missing winget, download failure, Python still absent after install,
and Doctor failure. They invoke PowerShell but do not download or install Python.
The actual installer/probe/reinstall passed with Python already installed. A clean
Windows machine's first-time automatic-download path remains unverified end to end.

An initial WSL run from the mounted Windows venv/source hit startup deadlines and
test-environment assumptions (Python PATH and bundled example files). The corrected
independent Linux-local environment passed; production deadlines were not increased.
Model discovery has no price field: the bounded lightweight allowlist does not prove
lowest current price. Authentication, quota, timeout, transport and unknown errors
never initiate fallback; all model selections share the same 15-second deadline.

## v0.1.1 — 2026-10-03, Windows

**Status: PASS for the Windows installer and authenticated inference probe.**

```text
Python:                    3.12.10
Codex CLI:                 0.160.0
PowerShell installer:      PASS
Idempotent reinstall:      PASS
Installed plugin:          NextPrompt 0.1.1, enabled
Doctor inference probe:    PASS — one short suggestion
PowerShell syntax:         PASS
Skill validation:          PASS — all six skills
python -m ruff check .     PASS
python -m ruff format --check .
                           PASS — 41 files already formatted
python -m pytest -q        PASS — 210 passed, 6 skipped in 2.40s
git diff --check           PASS
```

This Windows session initially had no working `python` command. Python 3.12.10 was
installed for the current user through the official `winget` package and its verified
installer, and the refreshed user PATH resolved the interpreter. The final
`scripts/install.ps1` then completed twice, including an opt-in `-Probe` run. It
preserved the Codex desktop process PATH, refreshed the plugin cache to 0.1.1 and did
not request elevation. Hook trust and clipboard consent remain explicit user actions.

## v0.1.0 — 2026-10-03, Linux

**Status: PARTIAL.** Implementation and local CLI integration passed. Authenticated
remote inference/quota and real desktop clipboard round trips remain unverified.

## Executed checks

```text
Python:        3.12.14
Codex CLI:     0.159.0-alpha.3
Platform:      Linux, SSH/headless
Clipboard:     unavailable
Catalog model: gpt-5.6-luna, reasoning low

python -m ruff check .                    PASS
python -m ruff format --check .           PASS
NEXTPROMPT_RUN_CLI_INTEGRATION=1
  python -m pytest -q                     216 passed in 13.18s
git diff --cached --check                 PASS
```

The complete suite contains **211 unit/process tests and 5 opt-in CLI integration
cases**. The exact elapsed time is one recorded full run, not a latency benchmark.

## Real CLI, simulated model service

- Registered the shipped local marketplace using the actual CLI.
- Installed/listed/removed the plugin; verified v0.1.0 metadata and cached files.
- Generated a bounded suggestion through the actual Codex child process and a
  loopback Responses service, using official provider configuration in a test launcher.
- Verified selected model/low reasoning and absence of shell, web, MCP and patch tools
  in the tested lightweight inference request.
- Ran a real root turn with the installed Stop hook. Recorded its synthetic output
  using a test-only observer and forwarded the exact JSON to Codex.
- Verified English and Chinese/emoji Hook output under an ASCII Python pipe setting.
- Verified one root inference plus one suggestion inference; no recursive suggestion,
  continuation or automatic next task.
- Verified only the root Codex transcript persisted; child exec was ephemeral and
  unique inference directories were removed.
- Injected a model authentication failure and verified the root task still succeeded.
  Codex transport retries were distinguishable from a second root task.

This does not validate remote model quality, account entitlement, pricing or billing.
The test-only trust bypass and provider launcher are not part of production setup.

## Privacy, guards and platforms

Tests cover the last-five selection, strict formatted-context limits, malformed and
missing transcripts, canonical/event formats, hidden/tool/image filtering, Unicode,
secret redaction before trimming and before provider mocks, generic/oversized output
rejection, obvious completed-work repetition, atomic concurrent config updates,
explicit setup consent, clipboard failure, cooldown and silent unexpected errors.
The re-entry guard runs before config/context access; disabled mode does not parse
transcripts, invoke inference, touch the clipboard or update state. Real process
tests verify bounded timeouts and termination of pipe-inheriting descendants.
Doctor now returns exit code 1 for real inference failure, even when login status
and catalog discovery pass. Authentication/quota diagnostics retain only fixed
categories. A repeated real probe returned `authentication` and exit code 1 here;
no credentials were changed.

All platform detection/backend-order/Unicode payload tests use mocks. Windows,
WSL, macOS, Wayland and X11 are **supported by implementation**, not marked as real
desktop Tested. This executor lacks a clipboard backend, so no clipboard was
overwritten and no clipboard restore was necessary. OSC 52 is off by default.

CI is configured for Ubuntu/Windows/macOS and Python 3.10/3.12. Hosted results are
available to the owner in the private repository's
[Actions page](https://github.com/Jineggegg/NextPrompt/actions).
Local execution used Python 3.12 on headless Linux.

## External blockers and interface differences

1. Login status reports ChatGPT, but a real isolated inference returns 401 / invalid
   token. Only Codex's normal external authentication flow can resolve this. OAuth
   reuse, subscription quota and remote model latency could not be established.
2. No local desktop/Windows clipboard exists for a real Unicode round trip.
3. Current portable root manifest hooks were skipped by the real CLI and examined
   source. The shipped plugin uses the official working legacy manifest instead.
4. Hook text is an official UI warning with Codex provenance, not assistant text or
   a copy button. Experimental thread prediction is not a plugin composer API.
5. `Stop` is a completion checkpoint. Another plugin's blocking Stop hook can still
   request continuation after this hook runs; no public aggregate-final-stop field
   exists. NextPrompt never requests continuation and skips `stop_hook_active` runs.

Source delivery targets the personal private repository `Jineggegg/NextPrompt`,
with a feature PR into `main`. No public release or package publication is planned.
The owner can install the plugin from an authenticated checkout and follow
[the local checklist](LOCAL_TEST.md) for real-account and desktop validation.
