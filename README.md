# NextPrompt

下一句，已经准备好了。 · Your next prompt, ready to paste.

NextPrompt 在 Codex 每轮回答完成后，生成一句贴合当前对话的下一步提示词。
安装时选择 **Y**，建议就会**自动复制到剪贴板**，按 **Ctrl+V**（macOS：**Cmd+V**）即可继续。

- **几秒就绪**：15 轮真实模型测试中，11 轮为 3–5 秒，平均 4.37 秒。
- **轻量开销**：只取最近 5 条消息，使用轻量模型和 `low` 思考，输出一句简短建议。
- **自动复制**：支持 Windows、WSL、macOS 和常见 Linux 桌面；也可以选择仅展示。
- **由你决定发送**：不会自动提交或执行建议。

NextPrompt suggests one short next instruction after each Codex turn. Choose **Y** during installation to **automatically copy suggestions to your clipboard**, then paste with **Ctrl+V** (**Cmd+V** on macOS).

- **Ready in seconds**: 11 of 15 measured turns took 3–5 seconds; average 4.37 seconds.
- **Lightweight**: the last 5 messages, a lightweight model with `low` reasoning, and one short suggestion.
- **Optional auto-copy**: Windows, WSL, macOS and common Linux desktops; display-only mode is also available.
- **You stay in control**: suggestions are never automatically sent or executed.

版本 / Version **0.1.5** · Python **3.10+** · Codex CLI **0.159+** · **MIT**

## 安装 / Installation

Windows：

```powershell
gh repo clone Jineggegg/NextPrompt
Set-Location NextPrompt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

目前仓库为私有，需要有仓库访问权限并登录 GitHub。公开后任何人都可以下载。
需提前安装并登录 Codex CLI；Python 缺失或版本过旧时，Windows 安装脚本通过 `winget` 自动安装。
安装时询问是否自动复制到剪贴板：**Y 开启，N 或直接回车仅展示**，结束报告会确认所选模式。

The repository is currently private: GitHub login and repository access are required. Once public, anyone can download it.
Install and sign in to Codex CLI first. On Windows, the installer uses `winget` to install Python if it is missing or too old.
When asked about clipboard copy, **Y enables auto-copy; N or Enter keeps display-only mode**. The final report confirms your choice.

安装结束后 / After installation:

1. 完全退出并重新打开 Codex。 / Quit and reopen Codex.
2. 打开 `/hooks`，检查并信任 NextPrompt 的 Stop Hook。 / Open `/hooks`, review and trust the NextPrompt Stop Hook.
3. 完成一轮普通对话；生成建议后，粘贴、检查，再发送。 / Complete a normal turn, then paste, review and send the suggestion.

不需要另行运行 setup。想修改偏好时使用 `$nextprompt-setup`。
无人值守安装可显式加 `-AutoCopy on` 或 `-AutoCopy off`。

No separate setup is required. Use `$nextprompt-setup` to change preferences.
For unattended installation, explicitly pass `-AutoCopy on` or `-AutoCopy off`.

macOS / Linux 或手动安装（需已有可用的 `python` 与 Codex）：

macOS / Linux or manual installation (working `python` and Codex required):

```sh
gh repo clone Jineggegg/NextPrompt
cd NextPrompt
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
```

同样需要重启并信任 Hook；手动安装默认仅展示，可用 `$nextprompt-setup` 开启自动复制。

Restart Codex and trust the Hook here too. Manual installation defaults to display-only; enable auto-copy with `$nextprompt-setup`.

## 显示示例 / What you see

开启自动复制后 / With auto-copy enabled:

```text
Next → 运行完整回归测试，检查最终改动。
✓ Copied to clipboard
```

剪贴板里只有建议正文。选择仅展示时显示 `Next prompt:`；复制失败时保留建议供手动复制。

Only the suggestion text is copied. Display-only mode uses `Next prompt:`; if copying fails, the suggestion remains available to copy manually.

## 常用命令 / Commands

| 命令 / Command | 用途 / Purpose |
| --- | --- |
| `$nextprompt` | 手动生成建议 / Generate a suggestion |
| `$nextprompt-setup` | 修改复制与模型设置 / Configure clipboard and model |
| `$nextprompt-status` | 查看状态 / Show status |
| `$nextprompt-enable` / `$nextprompt-disable` | 开启 / 关闭 / Enable / Disable |
| `$nextprompt-doctor` | 检查安装与连接 / Check installation and connection |

## 更多信息 / More information

速度因模型和网络而异；Token 用量尚未完整计量，独立请求会消耗模型额度。
仅使用最近的对话，不扫描项目，不保存对话副本；剪贴板复制需要你明确选择开启。

Speed varies by model and network. Full token usage has not been measured; separate requests consume model quota.
Only recent conversation is used: no project scanning or saved conversation copies. Clipboard copy requires your opt-in.

- [完整使用说明 / Full guide](docs/GUIDE.md)
- [中文安装与排查 / Chinese installation guide](docs/LOCAL_TEST.md)
- [测试结果与 15 轮实测 / Validation and 15-turn benchmark](docs/VALIDATION.md)
- [安全说明 / Security](SECURITY.md) · [参与贡献 / Contributing](CONTRIBUTING.md) · [MIT 许可证 / License](LICENSE)
