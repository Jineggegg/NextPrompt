# Codex Next Prompt

Your next prompt, ready to paste.

Codex Next Prompt is a plugin for the OpenAI Codex CLI that automatically generates your next prompt
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

Version **0.1.13** · Python **3.9+** · Codex CLI **0.159+** · **MIT**

## Installation

Install Git, then install and sign in to Codex CLI first.

Windows:

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
3. On the first trusted session start, a one-time usage report appears; complete a normal turn, then review, paste and send the suggestion yourself.

No separate setup is required. Use `$nextprompt-setup` to change preferences.

Manual installation:

```sh
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
```

Codex's own install commands print no instructions; the usage report appears at the first session
after you restart and trust the Hook. Manual installation also copies and notifies by default; turn
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

## Commands

| Command | Purpose |
| --- | --- |
| `$nextprompt` | Generate a suggestion |
| `$nextprompt-setup` | Configure clipboard, notifications, model and language |
| `$nextprompt-status` | Show status and local usage counts |
| `$nextprompt-enable` / `$nextprompt-disable` | Enable / Disable |
| `$nextprompt-doctor` | Check installation and connection |

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
