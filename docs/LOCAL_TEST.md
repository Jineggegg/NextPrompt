# 本地安装与验证

源码位于 GitHub 仓库 `Jineggegg/NextPrompt`，使用 Git 克隆即可。
运行环境需要 Codex CLI 0.159.0+，
并且 `codex exec --help` 必须具有
`--ignore-user-config`、`--ignore-rules`、`--ephemeral`、`--disable`。运行时需要
PATH 中有 Python 3.9+ 的 `python` 或 `python3`（macOS 自带的即可）（Hook 会先试 `python`，再回退到 `python3`）；不要把凭据写进 Git URL、脚本或项目文件。

## 1. Windows 一键安装

```powershell
git clone https://github.com/Jineggegg/NextPrompt.git
Set-Location NextPrompt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

脚本仅在用户主动运行时检查 Python（`python`、`python3`、`py -3` 都认）。缺少 Python 3.9+ 时，它通过官方
`winget` 源为当前用户静默安装 Python 3.12，刷新当前 PowerShell 的 PATH，
随后注册 marketplace、安装插件并运行 Doctor。它不申请管理员权限，Hook
和日常运行也不会下载软件。缺少 `winget` 时，脚本从 python.org 下载官方安装包，
确认是 Python Software Foundation 签名后才运行，签名不对就删除并停止。`-ExecutionPolicy Bypass` 仅对此次 PowerShell 进程生效，不会修改
系统策略。可选 `-Probe` 会发送固定模拟对话并可能消耗模型额度。

## 2. 手动安装并验证真实模型

```sh
git clone https://github.com/Jineggegg/NextPrompt.git
cd NextPrompt
codex --version
python --version
codex login status
python scripts/doctor.py --probe
```

如果显示 `authentication`，在自己的机器上运行 `codex login`，然后重试
Doctor。`--probe` 只发送固定的模拟对话，可能消耗自己的模型额度。必须看到
`Inference probe ✓ one short suggestion`；仅有登录成功或模型列表不够。
模型不可用时查看配置并选取自己有权限使用的轻量模型。不会自动改用大模型。
退出码 1 表示必要检查失败。剪切板不可用不会使 display-only 检查失败。

开发环境的真实请求返回 401，所以尚未证明真实账户额度或模型质量。
这个问题必须通过本地 Codex 的正常认证解决，插件不读取或复制 token。

## 3. 安装插件和 skills

```sh
codex plugin marketplace add .
codex plugin add nextprompt@nextprompt
codex
```

重启已有 Codex 会话。在 `/hooks` 中检查并信任 NextPrompt 的 Stop hook。
手动安装默认就会自动复制建议并弹出系统通知，无需运行 `$nextprompt-setup`。
Windows 安装脚本会询问 `Choose Y or N [Y]`：选择 Y 或直接回车开启自动复制，
选择 N 只显示建议。无人值守时显式传入 `-AutoCopy on` 或 `-AutoCopy off`。
安装结束报告会按实际保存的选择显示 `Automatic clipboard copy: ON` 并
说明新建议会自动复制，或显示 `OFF` 并说明仅展示建议。
安装脚本结束时会展示完整退出并重启 Codex、打开 `/hooks`、检查并信任
NextPrompt Stop hook、完成一次普通对话的指引。安装不代表 Hook 已获信任，
脚本也不会代替用户批准。直接使用 `codex plugin add` 的用户同样需要这些步骤，
但 Codex 自带命令不会展示本脚本的定制提示；请按 README 的安装后指南操作。
macOS / Linux 可运行 `sh scripts/install.sh`，安装结束时会显示同样的中英文说明。
只下载 skills 不会注册自动 Hook，需要安装完整插件。
只有想关闭自动复制、关闭通知（`--notify off`）或修改其他设置时才运行 `$nextprompt-setup`。
脚本仅修改用户本次选择的剪贴板配置，其他已有设置保留。安装时不会立即复制任何内容，也不会
自动提交或执行建议；复制发生在 Hook 加载并获信任后的有效建议生成时。
旧配置的 `auto_copy: null` 按默认处理，会自动复制。macOS 第一次如果没有弹通知，
到「系统设置 → 通知」里允许「脚本编辑器（Script Editor）」发送通知。
skill 选择器可能将名称显示为 `nextprompt:nextprompt-setup` 等带命名空间的形式。

安装无需 pip。不要为普通使用绕过 hook 信任检查。插件使用官方
`.codex-plugin/plugin.json`；当前验证版本的 portable 根 manifest 没有加载 hooks。

## 4. 检查输出与复制

在自己的临时项目中完成一个简单任务，例如修复一个小问题，并要求只运行
相关测试。回答结束后应出现一条简短的 `Next prompt:` 建议。模型输出太泛化、
重复已完成工作或不合规时会被丢弃，所以不是每轮都必然显示建议。

开启 Auto Copy 后，确认出现 `Next → ...` 与 `✓ Copied to clipboard`。
粘贴到临时文本编辑器，剪切板应只有建议正文，不含 `Next →` 或状态文字。
插件不会按 Enter，不会自动执行建议。真实剪切板测试前如有需要先保存原内容。

可手动测试 Unicode 输入（English / 中文 / emoji）；默认 suggestion 为单行。
Windows 优先 PowerShell，WSL 优先 Windows `clip.exe`，macOS 使用 `pbcopy`，
Wayland 使用 `wl-copy`，X11 使用 `xclip` 或 `xsel`。当前开发环境没有桌面剪切板，
这些平台的真实 round-trip 尚需本地验证。缺少工具时插件会显示手动复制提示，
不会安装系统软件。OSC 52 默认关闭。

运行 `$nextprompt-status` 查看当前配置与 backend；`$nextprompt-doctor` 可排查。
关闭 `$nextprompt-disable` 后不应再读取会话、请求模型或操作剪切板。

## 5. 可选：运行测试

```sh
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

在 macOS/Linux 等 POSIX 环境中，另外运行真实 CLI 与本地模拟模型服务的集成测试：

```sh
NEXTPROMPT_RUN_CLI_INTEGRATION=1 python -m pytest -q
```

集成测试使用独立的临时 Codex home，不使用真实 token 或远程模型。
真实推理和剪切板验证结果可由仓库所有者记录到 `docs/VALIDATION.md`。

## 6. 更新或卸载

`git pull` 后，移除再安装插件以刷新缓存，并重新检查 hook 信任。

```sh
codex plugin remove nextprompt@nextprompt
codex plugin add nextprompt@nextprompt
```

彻底卸载时再运行 `codex plugin marketplace remove nextprompt`。
如需删除配置，只删除本插件的
`$CODEX_HOME/plugins/data/nextprompt-nextprompt`；默认 `CODEX_HOME` 为
`~/.codex`。不要删除整个 Codex home 或项目目录。
