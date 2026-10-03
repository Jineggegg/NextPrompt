# Validation

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
Installed plugin:          nextprompt@codex-prompty 0.1.1, enabled
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
[Actions page](https://github.com/Jineggegg/Codex-Prompty/actions).
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

Source delivery targets the personal private repository `Jineggegg/Codex-Prompty`,
with a feature PR into `main`. No public release or package publication is planned.
The owner can install the plugin from an authenticated checkout and follow
[the local checklist](LOCAL_TEST.md) for real-account and desktop validation.
