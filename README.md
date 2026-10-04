# NextPrompt

下一句，已经准备好了。 · Your next prompt, ready to paste.

NextPrompt 让 Codex 每次回答的最后一行都写上下一步建议，标签和建议都用你平时输入的语言（如 `下一步建议：…`、`Next prompt: …`、`次のプロンプト：…`），
并把冒号后面的内容**原样复制到剪贴板**，按 **Ctrl+V**（macOS：**Cmd+V**）即可继续。

- **回答结束即就绪**：建议由 Codex 当前模型顺手写出，不再另外请求模型，也能看到完整对话。
- **剪贴板与回答一致**：剪贴板里就是建议行冒号后面的文字，不做改写；含疑似密钥时不复制。
- **自动兜底**：某次回答没写建议行时，改用轻量模型（`low` 思考、最近 5 条消息）生成一句。
- **多语言**：用你的语言给建议；提示文字跟随你最近的消息切换，支持 中文（简体/繁體）、日本語、한국어、English、Español、Français、Deutsch、Português、Русский。
- **自动复制 + 通知**：默认开启，建议一准备好就复制到剪贴板并弹出系统通知，看到通知即可粘贴；支持 Windows、WSL、macOS 和常见 Linux 桌面，也可以改为仅展示。
- **由你决定发送**：不会自动提交或执行建议。

NextPrompt makes every Codex reply end with a next-step line whose label and suggestion follow the language you write in (`Next prompt: …`, `下一步建议：…`, `次のプロンプト：…` and so on) and **copies the text after the colon to your clipboard exactly as shown**, so you can paste with **Ctrl+V** (**Cmd+V** on macOS).

- **Ready when the reply ends**: your Codex model writes the suggestion itself, with the whole conversation in view and no extra model request.
- **Clipboard matches the reply**: the copied text is the line's text, unchanged; lines that look like they contain a secret are not copied.
- **Automatic fallback**: if a reply has no such line, a lightweight model (`low` reasoning, last 5 messages) writes one.
- **Multilingual**: suggestions come in your language, and labels follow your latest message: 中文（简体/繁體）、日本語、한국어、English、Español、Français、Deutsch、Português、Русский.
- **Auto-copy + notification by default**: each suggestion is copied and announced with a desktop notification, so you know when to paste; Windows, WSL, macOS and common Linux desktops. Display-only mode is available.
- **You stay in control**: suggestions are never automatically sent or executed.

版本 / Version **0.1.11** · Python **3.9+** · Codex CLI **0.159+** · **MIT**

## 安装 / Installation

Windows：

```powershell
git clone https://github.com/Jineggegg/NextPrompt.git
Set-Location NextPrompt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

需提前安装 Git，并安装、登录 Codex CLI；Python 缺失或低于 3.9 时，Windows 安装脚本会自动安装（优先用 `winget`，没有 `winget` 就从 python.org 下载经过签名校验的官方安装包）。
安装时询问是否自动复制到剪贴板：**Y 或直接回车开启（默认），N 仅展示**。安装结束报告会说明使用步骤、复制设置和默认开启的桌面通知；通知可通过 `$nextprompt-setup` 关闭，不必关闭任何 Hook。

Install Git, then install and sign in to Codex CLI first. On Windows, the installer installs Python if it is missing or older than 3.9 (through `winget`, or the signature-checked official python.org installer when `winget` is unavailable).
When asked about clipboard copy, **Y or Enter enables auto-copy (default); N keeps display-only mode**. The final installation report explains how to use NextPrompt, confirms clipboard behavior, and notes that desktop notifications are on by default and can be turned off with `$nextprompt-setup` without disabling a Hook.

安装结束后 / After installation:

1. 完全退出并重新打开 Codex。 / Quit and reopen Codex.
2. 打开 `/hooks`，检查并信任 NextPrompt 的 SessionStart、UserPromptSubmit 和 Stop Hook。 / Open `/hooks`, review and trust the NextPrompt SessionStart, UserPromptSubmit and Stop Hooks.
3. 首次受信任的会话启动时，NextPrompt 会显示一次使用报告；完成一轮普通对话后，检查建议、粘贴并自行发送。 / On the first trusted session start, NextPrompt shows a one-time usage report; complete a normal turn, then review, paste and send the suggestion yourself.

不需要另行运行 setup。想修改偏好时使用 `$nextprompt-setup`。
无人值守安装可显式加 `-AutoCopy on` 或 `-AutoCopy off`。

No separate setup is required. Use `$nextprompt-setup` to change preferences.
For unattended installation, explicitly pass `-AutoCopy on` or `-AutoCopy off`.

macOS / Linux（需已安装 Codex；没有 Python 3.9+ 时脚本会自动安装：macOS 用 Homebrew 或苹果命令行工具，Linux 用系统包管理器）：

macOS / Linux (Codex required; if Python 3.9+ is missing, the script installs it through Homebrew or Apple's Command Line Tools on macOS, or the system package manager on Linux):

```sh
git clone https://github.com/Jineggegg/NextPrompt.git
cd NextPrompt
sh scripts/install.sh
```

安装脚本和 Windows 版一样询问是否自动复制，结束时立刻显示中英文使用说明。无人值守时加 `--auto-copy on` 或 `--auto-copy off`。

Like the Windows installer, it asks about clipboard copy and prints a bilingual usage report as soon as installation finishes. For unattended installation, pass `--auto-copy on` or `--auto-copy off`.

手动安装 / Manual installation:

```sh
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
```

Codex 自带的安装命令不会显示说明，说明会在重启并信任 Hook 后的第一次会话出现；手动安装同样默认自动复制并弹通知，可用 `$nextprompt-setup` 关闭。

Codex's own install commands print no instructions; the usage report appears at the first session after you restart and trust the Hook. Manual installation also copies and notifies by default; turn either off with `$nextprompt-setup`.

## 显示示例 / What you see

用中文对话时，Codex 回答的最后一行 / The last line of a Codex reply in a Chinese conversation:

```text
下一步建议：运行完整回归测试，检查最终改动。
```

Hook 随后提示 / The Hook then reports:

```text
✓ 已复制到剪贴板
```

剪贴板里是 `运行完整回归测试，检查最终改动。`，与这一行冒号后的文字完全相同；复制失败时可手动复制。
回答没写建议行、改由轻量模型兜底时，Hook 会显示 `下一句 → …` 并复制同一句。想固定界面语言，用 `$nextprompt-setup` 设置 `--language`（如 `zh`、`en`、`ja`）。

The clipboard holds exactly the text after the colon. If copying fails, copy it manually. When the lightweight fallback writes the suggestion, the Hook shows `Next → …` and copies that same sentence. To pin the label language, set `--language` (for example `zh`, `en`, `ja`) with `$nextprompt-setup`.

## 工作方式 / How it works

会话开始（以及对话压缩后）时，SessionStart Hook 给 Codex 当前模型一段说明；你每发一条消息，UserPromptSubmit Hook
再提醒一行，要求回答最后一行写建议。回答结束时 Stop Hook 读取这一行并复制。这是给模型的指令，绝大多数回答会照做，
个别没写时由轻量模型兜底。建议行会占用主模型少量输出。想回到旧方式（不在回答里写、单独请求轻量模型），用
`$nextprompt-setup` 设置 `--source model`。

At session start (and after compaction) a SessionStart Hook gives your Codex model a short instruction, and a
UserPromptSubmit Hook repeats a one-line reminder with each message, so every reply ends with the suggestion line.
The Stop Hook reads that line and copies it. It is an instruction to the model, not a hard guarantee; replies
without the line use the lightweight fallback. The line costs the root model a few output tokens. To go back to
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

Speed varies by model and network. Full token usage has not been measured; separate requests consume model quota.
Only recent conversation is used: no project scanning or saved conversation copies. Only the suggestion text is copied, and auto-copy can be turned off.

- [完整使用说明 / Full guide](docs/GUIDE.md)
- [中文安装与排查 / Chinese installation guide](docs/LOCAL_TEST.md)
- [测试结果与 15 轮实测 / Validation and 15-turn benchmark](docs/VALIDATION.md)
- [安全说明 / Security](SECURITY.md) · [参与贡献 / Contributing](CONTRIBUTING.md) · [MIT 许可证 / License](LICENSE)
