# NextPrompt

下一句，已经准备好了。

NextPrompt 在 Codex 每轮回答完成后，生成一句贴合当前对话的下一步提示词。
安装时选择 **Y**，建议就会**自动复制到剪贴板**，按 **Ctrl+V**（macOS：**Cmd+V**）即可继续。

- **几秒就绪**：15 轮真实模型测试中，11 轮为 3–5 秒，平均 4.37 秒。
- **轻量开销**：只取最近 5 条消息，使用轻量模型和 `low` 思考，输出一句简短建议。
- **自动复制**：支持 Windows、WSL、macOS 和常见 Linux 桌面；也可以选择仅展示。
- **由你决定发送**：不会自动提交或执行建议。

Lightweight next-prompt suggestions for Codex, with opt-in automatic clipboard copy.

版本 **0.1.5** · Python **3.10+** · Codex CLI **0.159+** · **MIT**

## 安装

Windows：

```powershell
gh repo clone Jineggegg/NextPrompt
Set-Location NextPrompt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

目前仓库为私有，需要有仓库访问权限并登录 GitHub。公开后任何人都可以下载。
需提前安装并登录 Codex CLI；Python 缺失或版本过旧时，Windows 安装脚本通过 `winget` 自动安装。
安装时询问是否自动复制到剪贴板：**Y 开启，N 或直接回车仅展示**，结束报告会确认所选模式。

安装结束后：

1. 完全退出并重新打开 Codex。
2. 打开 `/hooks`，检查并信任 NextPrompt 的 Stop Hook。
3. 完成一轮普通对话；生成建议后，粘贴、检查，再发送。

不需要另行运行 setup。想修改偏好时使用 `$nextprompt-setup`。
无人值守安装可显式加 `-AutoCopy on` 或 `-AutoCopy off`。

macOS / Linux 或手动安装（需已有可用的 `python` 与 Codex）：

```sh
gh repo clone Jineggegg/NextPrompt
cd NextPrompt
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
```

同样需要重启并信任 Hook；手动安装默认仅展示，可用 `$nextprompt-setup` 开启自动复制。

## 你会看到什么

开启自动复制后：

```text
Next → 运行完整回归测试，检查最终改动。
✓ Copied to clipboard
```

剪贴板里只有建议正文。选择仅展示时显示 `Next prompt:`；复制失败时保留建议供手动复制。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `$nextprompt` | 手动生成一句建议 |
| `$nextprompt-setup` | 修改自动复制、模型等设置 |
| `$nextprompt-status` | 查看状态 |
| `$nextprompt-enable` / `$nextprompt-disable` | 开启 / 关闭 |
| `$nextprompt-doctor` | 检查安装与模型连接 |

## 更多信息

速度因模型和网络而异；Token 用量尚未完整计量，独立请求会消耗模型额度。
仅使用最近的对话，不扫描项目，不保存对话副本；剪贴板复制需要你明确选择开启。

- [完整使用说明](docs/GUIDE.md)
- [中文安装与排查](docs/LOCAL_TEST.md)
- [测试结果与 15 轮实测](docs/VALIDATION.md)
- [安全说明](SECURITY.md) · [参与贡献](CONTRIBUTING.md) · [MIT 许可证](LICENSE)
