# NextPrompt

下一句，已经准备好了。 · Your next prompt, ready to paste.

NextPrompt 在 Codex 每轮回答完成后，生成一句贴合当前对话的下一步提示词。
安装时选择 **Y**，建议就会**自动复制到剪贴板**，按 **Ctrl+V**（macOS：**Cmd+V**）即可继续。

- **几秒就绪**：15 轮真实模型测试中，11 轮为 3–5 秒，平均 4.37 秒。
- **轻量开销**：只取最近 5 条消息，使用轻量模型和 `low` 思考，输出一句简短建议；Codex 检查结果缓存 12 小时，每轮少启动 3 次 Codex。
- **多语言**：用你的语言给建议；提示文字跟随你最近的消息切换，支持 中文（简体/繁體）、日本語、한국어、English、Español、Français、Deutsch、Português、Русский。
- **自动复制 + 通知**：默认开启，建议一准备好就复制到剪贴板并弹出系统通知，看到通知即可粘贴；支持 Windows、WSL、macOS 和常见 Linux 桌面，也可以改为仅展示。
- **由你决定发送**：不会自动提交或执行建议。

NextPrompt suggests one short next instruction after each Codex turn. Choose **Y** during installation to **automatically copy suggestions to your clipboard**, then paste with **Ctrl+V** (**Cmd+V** on macOS).

- **Ready in seconds**: 11 of 15 measured turns took 3–5 seconds; average 4.37 seconds.
- **Lightweight**: the last 5 messages, a lightweight model with `low` reasoning, and one short suggestion; Codex checks are cached for 12 hours, saving three Codex startups per turn.
- **Multilingual**: suggestions come in your language, and labels follow your latest message: 中文（简体/繁體）、日本語、한국어、English、Español、Français、Deutsch、Português、Русский.
- **Auto-copy + notification by default**: each suggestion is copied and announced with a desktop notification, so you know when to paste; Windows, WSL, macOS and common Linux desktops. Display-only mode is available.
- **You stay in control**: suggestions are never automatically sent or executed.

版本 / Version **0.1.9** · Python **3.9+** · Codex CLI **0.159+** · **MIT**

## 安装 / Installation

Windows：

```powershell
git clone https://github.com/Jineggegg/NextPrompt.git
Set-Location NextPrompt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

需提前安装 Git，并安装、登录 Codex CLI；Python 缺失或版本过旧时，Windows 安装脚本通过 `winget` 自动安装。
安装时询问是否自动复制到剪贴板：**Y 或直接回车开启（默认），N 仅展示**，结束报告会确认所选模式。

Install Git, then install and sign in to Codex CLI first. On Windows, the installer uses `winget` to install Python if it is missing or too old.
When asked about clipboard copy, **Y or Enter enables auto-copy (default); N keeps display-only mode**. The final report confirms your choice.

安装结束后 / After installation:

1. 完全退出并重新打开 Codex。 / Quit and reopen Codex.
2. 打开 `/hooks`，检查并信任 NextPrompt 的 SessionStart、UserPromptSubmit 和 Stop Hook。 / Open `/hooks`, review and trust the NextPrompt SessionStart, UserPromptSubmit and Stop Hooks.
3. 完成一轮普通对话；生成建议后，粘贴、检查，再发送。 / Complete a normal turn, then paste, review and send the suggestion.

不需要另行运行 setup。想修改偏好时使用 `$nextprompt-setup`。
无人值守安装可显式加 `-AutoCopy on` 或 `-AutoCopy off`。

No separate setup is required. Use `$nextprompt-setup` to change preferences.
For unattended installation, explicitly pass `-AutoCopy on` or `-AutoCopy off`.

macOS / Linux 或手动安装（需已有 Python 3.9+ 的 `python` 或 `python3` 命令，macOS 自带的即可，以及 Codex）：

macOS / Linux or manual installation (Python 3.9+ as `python` or `python3`, including the one bundled with macOS, plus Codex):

```sh
git clone https://github.com/Jineggegg/NextPrompt.git
cd NextPrompt
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
```

同样需要重启并信任 Hook；手动安装同样默认自动复制并弹通知，可用 `$nextprompt-setup` 关闭。

Restart Codex and trust the Hook here too. Manual installation also copies and notifies by default; turn either off with `$nextprompt-setup`.

## 显示示例 / What you see

默认情况下，Codex 当前模型会在每次回答的最后一行写上建议；中文对话用 `下一步：`，其他语言用 `Next prompt:`。
回答结束时 Hook 把这一行冒号后面的文字原样复制到剪贴板，所以回答末尾看到的建议和剪贴板里的内容完全一致：

By default, your Codex model ends every reply with the suggestion: `下一步：` in Chinese conversations,
`Next prompt:` otherwise. When the reply ends, the Hook copies the text after the label to your clipboard exactly
as written, so the line you see and the clipboard always match:

```text
……（回答正文 / the reply）
下一步：给登出流程加一个回归测试
✓ 已复制到剪贴板
```

这一行由会话开始时的说明和每轮一句简短提醒（UserPromptSubmit Hook）要求写出，不再另外请求轻量模型，几乎没有等待；
它是对模型的指令，模型偶尔仍可能漏写。某次回答没有这一行时，NextPrompt 退回到轻量模型生成建议，并在提示里显示出来。
这一行包含疑似密钥或控制字符时，不复制任何内容，也不会换成另一条建议。

A session-start instruction plus a one-line reminder on every turn (UserPromptSubmit Hook) ask for this line, with no
separate model request and almost no wait. It is an instruction, so the model can still occasionally skip it; then
NextPrompt falls back to the lightweight model and shows that suggestion in the Hook message. A line that looks
like a secret or contains control characters is not copied, and no different suggestion is copied in its place.

剪贴板里只有建议正文；复制失败时，建议仍在回答末尾，可以手动复制。想固定标签语言，用 `$nextprompt-setup` 设置 `--language`（如 `zh`、`en`）。

Only the suggestion text is copied; if copying fails, it stays at the end of the reply to copy manually. To pin the
label language, set `--language` (for example `zh`, `en`) with `$nextprompt-setup`.

## 改用独立轻量模型（可选）/ Use a separate lightweight model (optional)

`$nextprompt-setup` 设置 `--source model` 后，回答里不再加这一行，改为每轮结束后由轻量模型另外生成建议，
复制到剪贴板并显示在 Hook 提示里（例如 `下一句 → 运行完整回归测试，检查最终改动。`），不占主模型输出，但要等几秒。

With `--source model`, replies no longer carry the line; a lightweight model generates the suggestion after each
turn, copies it and shows it in the Hook message (for example `Next prompt: Run the full regression suite and
review the final diff.`). It uses none of your main model's output but takes a few seconds.

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
