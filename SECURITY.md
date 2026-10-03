# Security

## Scope and privacy

V1 reads a bounded tail of the transcript path supplied by the official root Stop
hook, selects at most five natural-language messages and redacts common credentials
before inference. No transcript database, telemetry, remote NextPrompt backend or
raw-content logs are implemented. Only settings and empty setup/error cooldown
markers persist. The child Codex uses ephemeral sessions; the parent Codex's own
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
copy is therefore **explicit opt-in**, with an initial unset state. Selecting the
recommended Yes in a UI does not grant consent until the user actually answers.
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

## Reporting a vulnerability

Do not open a public issue containing credentials, private conversations, unredacted
rollouts or account files. Once this repository is hosted on GitHub, use its private
vulnerability reporting feature if enabled; otherwise contact its listed maintainer
privately before sharing sensitive details. No reporting address or GitHub account
is fabricated in this unpublished checkout. Include version, platform, a sanitized
description and a minimal synthetic reproduction.

Only v0.1.x is currently maintained. Fixes should include regression tests and a
changelog entry. Repository fixtures must use conspicuously fake credentials only.
