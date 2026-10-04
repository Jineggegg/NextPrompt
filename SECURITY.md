# Security

## Scope and privacy

V1 reads a bounded tail of the transcript path supplied by the official root Stop
hook, selects at most five natural-language messages and redacts common credentials
before inference. No transcript database, telemetry, remote NextPrompt backend or
raw-content logs are implemented. Only settings, empty error cooldown markers and
a capability cache (Codex executable fingerprint and model catalog) persist. The child Codex uses ephemeral sessions; the parent Codex's own
session storage is outside this plugin's control.

Redaction is defense in depth, not a complete data-loss prevention system. Unknown
credential formats, personal information and proprietary prose may still reach
the model service. Keep redaction enabled and review your model-service policies.
Untrusted conversation is treated as model data; inference is isolated from the
repository, shell, MCP, web and external-action extensions where official flags
allow. A local attacker controlling Codex, Python, clipboard executables, config
or the account can defeat these boundaries.

## Clipboard consent

Other applications on the system may read clipboard contents; clipboard managers,
remote desktops and OS clipboard sync can also retain or forward them. Automatic
copy is therefore **explicit opt-in**, with display-only mode as the default.
Installation and unanswered setup questions never grant clipboard consent.
Legacy unset clipboard settings also display suggestions without copying.
The copied payload is only the sanitized suggestion, not status text or context.
OSC 52 defaults off, is capability-gated and cannot verify terminal acceptance.

## Hook safety

Production installation requires official `/hooks` trust review. The integration
suite uses trust bypass only for vetted hooks in a disposable Codex home. Never
recommend global trust bypass to users. Stop output never includes `decision:block`,
`reason`, `continue:false` or exit code 2. Model instructions are never submitted
back into the main session automatically. The independent re-entry environment
guard exits before reading configuration or stdin. Disabled mode has no context,
inference, clipboard or state-write effects after its config read.

## Windows installer

The optional `scripts/install.ps1` runs only when the user invokes it. If Python
3.10+ is unavailable, it uses the official `winget` source to install Python 3.12
for the current user with no elevation, then refreshes the process PATH and verifies
the interpreter. The Hook and normal skill execution never download or install
software. If `winget` is unavailable or installation cannot be verified, the script
stops rather than falling back to an unverified download. The documented PowerShell
execution-policy override is process-scoped and does not modify system policy.

## Reporting a vulnerability

Do not open a public issue containing credentials, private conversations, unredacted
rollouts or account files. Report privately through GitHub's private vulnerability
reporting for [Jineggegg/NextPrompt](https://github.com/Jineggegg/NextPrompt/security)
(Security → Report a vulnerability). Include version, platform, a sanitized
description and a minimal synthetic reproduction.

Only v0.1.x is currently maintained. Fixes should include regression tests and a
changelog entry. Repository fixtures must use conspicuously fake credentials only.
