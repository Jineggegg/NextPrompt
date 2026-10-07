# Codex Next Prompt

Your next prompt, ready to paste.

Codex Next Prompt is a plugin for OpenAI Codex (the Codex app and Codex CLI) that automatically generates your next prompt
from the conversation context and copies it directly to your clipboard. When a next step is worth it,
Codex ends its reply with one natural sentence that quotes your likely next prompt
(`→ Want me to “add a regression test for logout”?`), and the quoted prompt is copied, so you can
paste with **Ctrl+V** (**Cmd+V** on macOS) and keep going.

- **Only when useful**: suggestions appear for a part you named but is not done yet, work this turn left unfinished, or resuming unfinished work after a side question; new ideas, confirmations, answers, wrapping up and stopping get none.
- **Varied wording**: wording shapes rotate within a session, so two suggestions in a row never read alike, in your language and tone.
- **Pastes as your own words**: the clipboard holds only the quoted prompt; Chinese prompts get a short go-ahead at the end. Lines that look like they contain a secret are not copied.
- **Ready when the reply ends**: your Codex model writes the suggestion itself, with the whole conversation in view and no extra model request.
- **Multilingual**: suggestions come in your language, and labels follow your latest message: English, Chinese (Simplified and Traditional), Japanese, Korean, Spanish, French, German, Portuguese and Russian.
- **Auto-copy + notification by default**: each suggestion is copied and announced with a desktop notification, so you know when to paste; Windows, WSL, macOS and common Linux desktops. Display-only mode is available.
- **You stay in control**: suggestions are never automatically sent or executed.

Version **0.2.3** · Python **3.9+** · Codex CLI **0.159+** · **MIT**

## Installation

The Codex app and Codex CLI share an installation only when they use the same `CODEX_HOME`
on the same host. Windows and WSL may use different Python installations, settings and clipboards.

### First-time setup

After installing from GitHub in Codex, run the plugin's **Setup** action (or type
`$nextprompt-onboarding`). It introduces the plugin, checks the real hook commands and
explains any remaining activation step, even if the hooks cannot start yet.
Installing from GitHub alone does **not** install Python or trust hooks.

On Windows, the hooks use the system PowerShell and look for Python in its default
installation folders before PATH. This avoids stale app PATHs and the Microsoft Store
Python aliases. The installer uses the same discovery logic. Missing Python produces
an actionable NextPrompt message instead of an unexplained hook failure.

### Install with Codex (easiest, works in the Codex app)

Paste this into a Codex chat. Codex runs the installer as one command, so you approve it once
(it needs network access and writes to `~/.codex`, outside the workspace):

````text
Install the Codex Next Prompt plugin from https://github.com/Jineggegg/codex-next-prompt.
Run exactly one of these as a single command, requesting approval once (it needs network access and writes outside the workspace). Do not split it, edit it or work around errors.

Windows (PowerShell):
$d = Join-Path $HOME 'codex-next-prompt'; if (Test-Path $d) { git -C $d pull --ff-only } else { git clone https://github.com/Jineggegg/codex-next-prompt.git $d }; if ($?) { powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $d 'scripts\install.ps1') -AutoCopy on -Notify on }

macOS / Linux:
d="$HOME/codex-next-prompt"; if [ -d "$d" ]; then git -C "$d" pull --ff-only; else git clone https://github.com/Jineggegg/codex-next-prompt.git "$d"; fi && sh "$d/scripts/install.sh" --auto-copy on --notify on

If git is missing, tell me to install Git and stop. If the command fails, show me its last lines and stop.
When it succeeds, introduce how suggestions and clipboard copy work. Tell me the remaining activation steps: fully quit and reopen Codex, then review and trust the NextPrompt SessionStart, UserPromptSubmit and Stop hooks in Codex Hook settings (CLI: /hooks). Installation success alone does not prove the hooks are active.
````

Python is installed automatically when missing. Trusting the hooks stays your own step.

### Install from a terminal

Install Git, then install and sign in to Codex (the app or Codex CLI) first. The Windows
installer also finds the Codex app's own `codex.exe` when no `codex` command is on PATH.

Windows (in **PowerShell**, not Command Prompt):

```powershell
git clone https://github.com/Jineggegg/codex-next-prompt.git
Set-Location codex-next-prompt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

The Windows installer installs Python if it is missing or older than 3.9 (through `winget`, or the
signature-checked official python.org installer when `winget` is unavailable).

macOS / Linux:

```sh
git clone https://github.com/Jineggegg/codex-next-prompt.git
cd codex-next-prompt
sh scripts/install.sh
```

If Python 3.9+ is missing, the script installs it through Homebrew or Apple's Command Line Tools on
macOS, or the system package manager on Linux, which falls back to a versioned package such as
`python3.12` when the default `python3` is too old.

Both installers first show the recommended settings: **auto-copy and desktop notifications both ON**.
Press Enter (or Y) to keep them; answer N, then two letters for copy and notifications, such as `yn`
(copy on, notifications off), `ny` (copy off, notifications on) or `nn` (both off). Then the
installation report appears: how to use Codex Next Prompt, the saved copy and notification settings,
and how to change them later with `$nextprompt-setup` without disabling a Hook.

For unattended installation, pass `-AutoCopy on|off` and `-Notify on|off` on Windows, or
`--auto-copy on|off` and `--notify on|off` on macOS / Linux; a setting you leave out keeps the
recommended value (on).

After installation:

1. Quit and reopen Codex.
2. Open `/hooks`, review and trust the NextPrompt SessionStart, UserPromptSubmit and Stop Hooks.
3. On the first trusted session start or user message, a one-time usage report appears. Try “Write a two-part outline; write only part one for now.” A follow-up for part two is expected; review, paste and send it yourself. Finished tasks normally produce no suggestion.

The installer saves preferences. The plugin Setup action explains activation; `$nextprompt-setup` changes preferences.

Manual installation:

```sh
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
```

Codex's terminal install commands may not print instructions. Run `$nextprompt-onboarding`
for an introduction and activation check, then restart and review Hook trust. Manual installation also copies and notifies by default; turn
either off with `$nextprompt-setup`.

## What you see

The last line of a Codex reply when the task continues (worded differently each time):

```text
→ One loose end: “fix the two failing logout tests”.
```

The Hook then reports:

```text
✓ Copied to clipboard
```

The clipboard holds the quoted prompt. If copying fails, copy it manually. A reply without a line
means no suggestion was worth it: nothing is copied or generated. To pin the label language, set
`--language` (for example `en`, `zh`, `ja`) with `$nextprompt-setup`.

## How it works

At session start (and after compaction) a SessionStart Hook gives your Codex model a short
instruction, and a UserPromptSubmit Hook repeats a short reminder with a rotating wording shape; the
model decides whether a suggestion is worth it. The Stop Hook reads the last line and copies the
quoted prompt. It is an instruction to the model, not a hard guarantee. The line costs the root model
a few output tokens. To go back to the previous behavior (no line in replies, a separate lightweight
request), set `--source model` with `$nextprompt-setup`.

Code blocks, quoted examples and fictional dialogue are not commands to copy. The
optional separate model returns a validated instruction-or-null object; malformed
output is skipped. Both modes follow the same unfinished-work policy.

## Commands

| Command | Purpose |
| --- | --- |
| `$nextprompt-onboarding` | First-use introduction and activation check |
| `$nextprompt` | Generate a suggestion |
| `$nextprompt-setup` | Configure clipboard, notifications, model and language |
| `$nextprompt-status` | Show status and local usage counts |
| `$nextprompt-enable` / `$nextprompt-disable` | Enable / Disable |
| `$nextprompt-doctor` | Check installation and connection |

### If nothing happens

Run `$nextprompt-doctor`. It runs all three shipped commands with synthetic input,
without copying anything, showing notifications, or requesting a model. A passing
self-test verifies startup, context injection and Stop handling, **not** hook trust.
Default inline suggestions do not need a separate Codex CLI login or model catalog;
those checks are only required by `--source model` or an explicit `doctor --probe`.

If Hook settings say **needs review**, review and trust the current definitions.
If a hook **fails**, use the onboarding action to repair Python discovery. Fully
restart Codex after installation. On WSLg, install `wl-clipboard` to copy through the Linux display when Windows
program interoperability is disabled. Without either bridge, suggestions display
only; use hooks on the Windows host for native Windows notifications.
The plugin never changes WSL interoperability or hook trust for you.

## Privacy

Only recent conversation is used: no project scanning or saved conversation copies. Only the
suggestion text is copied, and auto-copy can be turned off.

`$nextprompt-status` shows local counts: how many replies suggested something, and how many
suggestions you sent as is, sent with more words, or did not use. Only counts and short one-way
hashes are kept, never text; turn this off with `--stats off` or clear it with `--stats reset`
through `$nextprompt-setup`.

Speed varies by model and network. Full token usage has not been measured; the optional separate
request mode consumes model quota.

## More information

- [Full guide](docs/GUIDE.md)
- [Validation and 15-turn benchmark](docs/VALIDATION.md)
- [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [MIT License](LICENSE)
