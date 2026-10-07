# Verified Codex interfaces — 2026-10-03

Local CLI: `codex-cli 0.159.0-alpha.3`. Official repository inspected at
[`b172810921f89847cd310ecc496f9c901760e933`](https://github.com/openai/codex/tree/b172810921f89847cd310ecc496f9c901760e933).
The fetched upstream snapshot is not vendored and was not modified.

Commands executed: `codex --version`, `codex --help`, `codex exec --help`,
`codex plugin --help`, add/remove/marketplace help, `codex login status`,
`codex features list`, actual local install/remove, model discovery and exec.

| Requirement | Verified contract / result |
| --- | --- |
| Plugin install | `codex plugin marketplace add SOURCE`; `codex plugin add PLUGIN@MARKETPLACE`; local install is non-interactive |
| Manifest | `.codex-plugin/plugin.json` with skills/hooks paths works; portable manifest installation works but its hooks do not load in this snapshot |
| Skills | `skills/<name>/SKILL.md`, YAML name/description; explicit `$` picker and natural matching; namespace can qualify plugin skills |
| Lifecycle | Hooks feature; root `Stop`, distinct `SubagentStop`; `/hooks` trust review is required |
| Stop input | `session_id`, `turn_id`, `transcript_path` (nullable), `cwd`, `model`, `hook_event_name`, `permission_mode`, `last_assistant_message` (nullable), `stop_hook_active` |
| Stop output | Exit 0, empty or valid JSON; `systemMessage` surfaces a UI warning. Plain stdout text is invalid |
| Forbidden continuation | `decision: "block"` + `reason`, or exit 2, continues the agent. NextPrompt never emits these |
| Data | `PLUGIN_DATA` and `PLUGIN_ROOT` injected into plugin command hooks. Legacy data root: `$CODEX_HOME/plugins/data/<plugin>-<marketplace>` |
| Auth | `codex login status` reports ChatGPT. Actual inference returned 401 and invalid token. No entitlement/billing claim established |
| Model discovery | Official app-server handshake (`initialize`, `initialized`), `model/list`: model id, effort list; no prices; catalog is not access proof |
| Model/effort | `-m`, `-c model_reasoning_effort=...`; Luna present in catalog with lowest effort `low`, not `minimal` |
| Child inference | `codex exec`; `--ephemeral`, `--ignore-user-config` (auth still uses CODEX_HOME), `--ignore-rules`, read-only sandbox, stdin prompt |
| Approval | Exec rejects `-a`; use official `-c approval_policy="never"` |
| Recursion | Official `--disable hooks`, `--disable plugins`, plus independent early environment guard |
| Tool limits | Shell/apps/plugins/subagents/browser/images features can be disabled, web search disabled; no general stable `--no-tools` CLI flag found |
| Composer/TUI | No plugin copy-button/custom-component/composer-insertion API found. Experimental thread prediction exists but is not plugin UI injection |
| Clipboard here | Headless Linux; no `wl-copy`, `xclip`, `xsel`, `pbcopy`, Windows bridge. Real clipboard round trip unavailable |

## Documentation and source evidence

- [Build plugins](https://developers.openai.com/codex/plugins/build)
- [Hooks](https://developers.openai.com/codex/hooks)
- [Skills](https://developers.openai.com/codex/skills)
- [CLI reference](https://developers.openai.com/codex/cli/reference)
- [Authentication](https://developers.openai.com/codex/auth)
- [App-server/model discovery](https://developers.openai.com/codex/app-server)
- [Stop input schema](https://github.com/openai/codex/blob/b172810921f89847cd310ecc496f9c901760e933/codex-rs/hooks/schema/generated/stop.command.input.schema.json)
- [Stop output schema](https://github.com/openai/codex/blob/b172810921f89847cd310ecc496f9c901760e933/codex-rs/hooks/schema/generated/stop.command.output.schema.json)
- [Portable hooks skipped by loader](https://github.com/openai/codex/blob/b172810921f89847cd310ecc496f9c901760e933/codex-rs/core-plugins/src/loader.rs#L952)
- [Official plugin storage](https://github.com/openai/codex/blob/b172810921f89847cd310ecc496f9c901760e933/codex-rs/core-plugins/src/store.rs#L122)
- [Hook TUI rendering](https://github.com/openai/codex/blob/b172810921f89847cd310ecc496f9c901760e933/codex-rs/tui/src/history_cell/hook_cell.rs#L718)
- [Experimental prediction API types](https://github.com/openai/codex/blob/b172810921f89847cd310ecc496f9c901760e933/codex-rs/app-server-protocol/src/protocol/v2/thread_prediction.rs)

Current docs redirect some Codex pages to `learn.chatgpt.com/docs/...`. The links
above are the official entry URLs used during research. Runtime behavior and source
take precedence over documentation when they disagree. Portable manifest hook
loading was investigated after the real integration test exposed the discrepancy;
the shipped plugin therefore uses the working official legacy format.

NextPrompt does not inspect credential file contents, invent unsupported flags,
call an author-funded service, fork Codex, patch its TUI or emit a continuation.

## Activation and onboarding — 2026-10-07

Official [plugin packaging](https://developers.openai.com/plugins/build/plugins)
documents `extensions.com.openai.onboardingSkill`, including inside the legacy
`.codex-plugin/plugin.json`. Setup invokes the packaged skill independently of hooks.
The legacy layout is retained for Codex 0.159 compatibility.

Official [Hooks](https://learn.chatgpt.com/docs/hooks) requires review of the exact
hook definition. Installing or enabling a plugin does not grant trust; updated hook
commands need review again. NextPrompt does not write trust hashes.

Confirmed gaps in 0.2.1: the Windows installer discovered Python only on PATH while
hooks had additional install-folder fallbacks; Doctor checked bundle shape without
running commands and could reject inline-only installation on unrelated model/login
failures; welcome output required SessionStart, so installation into an existing
chat could miss it. The new installer and Windows hook share Python discovery, and
Doctor exercises SessionStart, UserPromptSubmit and Stop using disposable data.

A WSL runtime with `interop.enabled=false` and `appendWindowsPath=false` cannot run
Windows clipboard executables. WSLg offers an independent clipboard bridge through
`wl-copy`; the adapter now tries it when WAYLAND_DISPLAY exists. Without either
backend it reports display-only mode and does not change interoperability settings. A friend's precise historical Windows failure still
requires that machine's error details; the new self-test detects startup failure.
