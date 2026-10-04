# NextPrompt

下一句，已经准备好了。 · Your next prompt, ready to paste.

NextPrompt 让 Codex 在有值得做的下一步时，在回答最后用一句自然的话给出建议（如 `→ 要不要「给 PDF 加上目录」？`），
并把引号里的指令**复制到剪贴板**，按 **Ctrl+V**（macOS：**Cmd+V**）即可继续。

- **没必要就不给**：只在三种情况下建议——你说过但还没做的部分（下一章、下一页、留到后面的部分）、这一轮没做完或只查出原因的事、插问之后回到没做完的活；新点子、确认、问答、收尾、叫停都不给。
- **说法不重样**：同一会话里按顺序轮换说法（要不要「…」？/ 还差一步，「…」就齐了。/ 想继续的话，说「…」就行。…），相邻两条不会重复，用你的语言和语气。
- **粘贴就是你的话**：剪贴板里是引号里的指令，中文会加上“做吧”“来吧”之类的收尾（`给 PDF 加上目录，做吧`）；含疑似密钥时不复制。
- **回答结束即就绪**：建议由 Codex 当前模型顺手写出，不再另外请求模型，也能看到完整对话。
- **多语言**：用你的语言给建议；提示文字跟随你最近的消息切换，支持 中文（简体/繁體）、日本語、한국어、English、Español、Français、Deutsch、Português、Русский。
- **自动复制 + 通知**：默认开启，建议一准备好就复制到剪贴板并弹出系统通知，看到通知即可粘贴；支持 Windows、WSL、macOS 和常见 Linux 桌面，也可以改为仅展示。
- **由你决定发送**：不会自动提交或执行建议。

When a next step is worth it, NextPrompt has Codex end its reply with one natural sentence that quotes your likely next prompt (`→ Want me to “add a regression test for logout”?`) and **copies the quoted prompt to your clipboard**, so you can paste with **Ctrl+V** (**Cmd+V** on macOS).

- **Only when useful**: suggestions appear for a part you named but is not done yet, work this turn left unfinished, or resuming unfinished work after a side question; new ideas, confirmations, answers, wrapping up and stopping get none.
- **Varied wording**: wording shapes rotate within a session, so two suggestions in a row never read alike, in your language and tone.
- **Pastes as your own words**: the clipboard holds the quoted prompt; Chinese prompts get a short go-ahead such as `，做吧`. Lines that look like they contain a secret are not copied.
- **Ready when the reply ends**: your Codex model writes the suggestion itself, with the whole conversation in view and no extra model request.
- **Multilingual**: suggestions come in your language, and labels follow your latest message: 中文（简体/繁體）、日本語、한국어、English、Español、Français、Deutsch、Português、Русский.
- **Auto-copy + notification by default**: each suggestion is copied and announced with a desktop notification, so you know when to paste; Windows, WSL, macOS and common Linux desktops. Display-only mode is available.
- **You stay in control**: suggestions are never automatically sent or executed.

版本 / Version **0.1.13** · Python **3.9+** · Codex CLI **0.159+** · **MIT**

## 安装 / Installation

Windows：

```powershell
git clone https://github.com/Jineggegg/NextPrompt.git
Set-Location NextPrompt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

需提前安装 Git，并安装、登录 Codex CLI；Python 缺失或低于 3.9 时，Windows 安装脚本会自动安装（优先用 `winget`，没有 `winget` 就从 python.org 下载经过签名校验的官方安装包）。
安装时先显示推荐设置：**自动复制、桌面通知都开（推荐）**。直接回车（或 Y）保留；输入 N 后再用两个字母分别选择自动复制和通知，例如 `yn` 是复制开、通知关，`ny` 是复制关、通知开，`nn` 是都关。选完才显示安装结束报告：使用步骤、实际保存的复制和通知设置，以及以后如何用 `$nextprompt-setup` 修改，不必关闭任何 Hook。

Install Git, then install and sign in to Codex CLI first. On Windows, the installer installs Python if it is missing or older than 3.9 (through `winget`, or the signature-checked official python.org installer when `winget` is unavailable).
The installer first shows the recommended settings: **auto-copy and desktop notifications both ON**. Press Enter (or Y) to keep them; answer N, then two letters for copy and notifications, such as `yn` (copy on, notifications off), `ny` (copy off, notifications on) or `nn` (both off). Only then does the installation report appear: how to use NextPrompt, the saved copy and notification settings, and how to change them later with `$nextprompt-setup` without disabling a Hook.

安装结束后 / After installation:

1. 完全退出并重新打开 Codex。 / Quit and reopen Codex.
2. 打开 `/hooks`，检查并信任 NextPrompt 的 SessionStart、UserPromptSubmit 和 Stop Hook。 / Open `/hooks`, review and trust the NextPrompt SessionStart, UserPromptSubmit and Stop Hooks.
3. 首次受信任的会话启动时，NextPrompt 会显示一次使用报告；完成一轮普通对话后，检查建议、粘贴并自行发送。 / On the first trusted session start, NextPrompt shows a one-time usage report; complete a normal turn, then review, paste and send the suggestion yourself.

不需要另行运行 setup。想修改偏好时使用 `$nextprompt-setup`。
无人值守安装可显式加 `-AutoCopy on|off` 和 `-Notify on|off`；只给其中一个时，另一个用推荐值（开）。

No separate setup is required. Use `$nextprompt-setup` to change preferences.
For unattended installation, pass `-AutoCopy on|off` and `-Notify on|off`; a setting you leave out keeps the recommended value (on).

macOS / Linux（需已安装 Codex；没有 Python 3.9+ 时脚本会自动安装：macOS 用 Homebrew 或苹果命令行工具，Linux 用系统包管理器，系统默认的 python3 太旧时改装 `python3.12` 这类带版本号的包）：

macOS / Linux (Codex required; if Python 3.9+ is missing, the script installs it through Homebrew or Apple's Command Line Tools on macOS, or the system package manager on Linux, which falls back to a versioned package such as `python3.12` when the default `python3` is too old):

```sh
git clone https://github.com/Jineggegg/NextPrompt.git
cd NextPrompt
sh scripts/install.sh
```

安装脚本和 Windows 版一样先显示推荐设置并询问是否修改，结束时立刻显示中英文使用说明。无人值守时加 `--auto-copy on|off` 和 `--notify on|off`。

Like the Windows installer, it shows the recommended settings, asks whether to change them and prints a bilingual usage report as soon as installation finishes. For unattended installation, pass `--auto-copy on|off` and `--notify on|off`.

手动安装 / Manual installation:

```sh
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
```

Codex 自带的安装命令不会显示说明，说明会在重启并信任 Hook 后的第一次会话出现；手动安装同样默认自动复制并弹通知，可用 `$nextprompt-setup` 关闭。

Codex's own install commands print no instructions; the usage report appears at the first session after you restart and trust the Hook. Manual installation also copies and notifies by default; turn either off with `$nextprompt-setup`.

## 显示示例 / What you see

用中文对话、任务还有下一部分时，Codex 回答的最后一行（每次说法不同） / The last line of a Codex reply in a Chinese conversation when the task continues (worded differently each time):

```text
→ 还差一步，「修好那两个失败的登出测试」就齐了。
```

Hook 随后提示 / The Hook then reports:

```text
✓ 已复制到剪贴板
```

剪贴板里是 `修好那两个失败的登出测试，做吧`（引号里的指令加一个随机的收尾：做吧 / 来吧 / 开始吧 / 动手吧）；其他语言只复制引号里的指令。
复制失败时可手动复制。回答没写建议行就是这一步不需要建议，不复制也不另外生成。想固定界面语言，用 `$nextprompt-setup` 设置 `--language`（如 `zh`、`en`、`ja`）。

The clipboard holds the quoted prompt; Chinese prompts get a short go-ahead such as `，做吧`. If copying fails, copy it manually. A reply without a line means no suggestion was worth it: nothing is copied or generated. To pin the label language, set `--language` (for example `zh`, `en`, `ja`) with `$nextprompt-setup`.

## 工作方式 / How it works

会话开始（以及对话压缩后）时，SessionStart Hook 给 Codex 当前模型一段说明；你每发一条消息，UserPromptSubmit Hook
再提醒一行（并随机给一种说法），由模型判断这一步值不值得建议。回答结束时 Stop Hook 读取最后一行并复制引号里的指令。
这是给模型的指令，不是硬性保证。建议行会占用主模型少量输出。想回到旧方式（不在回答里写、单独请求轻量模型），用
`$nextprompt-setup` 设置 `--source model`。

At session start (and after compaction) a SessionStart Hook gives your Codex model a short instruction, and a
UserPromptSubmit Hook repeats a short reminder with a randomly chosen wording shape; the model decides whether a
suggestion is worth it. The Stop Hook reads the last line and copies the quoted prompt. It is an instruction to the
model, not a hard guarantee. The line costs the root model a few output tokens. To go back to
the previous behavior (no line in replies, a separate lightweight request), set `--source model` with `$nextprompt-setup`.

## 常用命令 / Commands

| 命令 / Command | 用途 / Purpose |
| --- | --- |
| `$nextprompt` | 手动生成建议 / Generate a suggestion |
| `$nextprompt-setup` | 修改复制、模型与显示语言 / Configure clipboard, model and language |
| `$nextprompt-status` | 查看状态 / Show status |
| `$nextprompt-enable` / `$nextprompt-disable` | 开启 / 关闭 / Enable / Disable |
| `$nextprompt-doctor` | 检查安装与连接 / Check installation and connection |

## 更多信息 / More information

速度因模型和网络而异；Token 用量尚未完整计量，独立请求会消耗模型额度。
仅使用最近的对话，不扫描项目，不保存对话副本；剪贴板里只放建议正文，可随时关闭自动复制。
`$nextprompt-status` 会显示本机统计：给了多少条建议、你原样发送 / 补充后发送 / 没用的各有多少。只记次数和无法还原的短哈希，不记任何文字；用 `$nextprompt-setup` 设置 `--stats off` 关闭，`--stats reset` 清零。

Speed varies by model and network. Full token usage has not been measured; separate requests consume model quota.
Only recent conversation is used: no project scanning or saved conversation copies. Only the suggestion text is copied, and auto-copy can be turned off.
`$nextprompt-status` shows local counts: how many replies suggested something, and how many suggestions you sent as is, sent with more words, or did not use. Only counts and short one-way hashes are kept, never text; turn this off with `--stats off` or clear it with `--stats reset` through `$nextprompt-setup`.

- [完整使用说明 / Full guide](docs/GUIDE.md)
- [中文安装与排查 / Chinese installation guide](docs/LOCAL_TEST.md)
- [测试结果与 15 轮实测 / Validation and 15-turn benchmark](docs/VALIDATION.md)
- [安全说明 / Security](SECURITY.md) · [参与贡献 / Contributing](CONTRIBUTING.md) · [MIT 许可证 / License](LICENSE)
