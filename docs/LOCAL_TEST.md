# 本地安装与验证

GitHub 交付目标是 `Jineggegg/Codex-Prompty` 私有仓库。仓库创建并推送完成后，
使用仓库所有者的 GitHub 账号克隆。运行环境需要 Codex CLI 0.159.0+，
并且 `codex exec --help` 必须具有
`--ignore-user-config`、`--ignore-rules`、`--ephemeral`、`--disable`。需要 PATH
中的 `python` 为 Python 3.10+；不要把凭据写进 Git URL、脚本或项目文件。

## 1. 克隆并验证真实模型

```sh
gh auth login
gh repo clone Jineggegg/Codex-Prompty
cd Codex-Prompty
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

## 2. 安装插件和 skills

```sh
codex plugin marketplace add .
codex plugin add nextprompt@codex-prompty
codex
```

重启已有 Codex 会话。在 `/hooks` 中检查并信任 NextPrompt 的 Stop hook。
然后运行 `$nextprompt-setup`。明确选择 Yes 才开启 Auto Copy；选择 No
则仅显示建议。建议先选择 No 验证，再通过同一 skill 开启复制。
skill 选择器可能将名称显示为 `nextprompt:nextprompt-setup` 等带命名空间的形式。

安装无需 pip。不要为普通使用绕过 hook 信任检查。插件使用官方
`.codex-plugin/plugin.json`；当前验证版本的 portable 根 manifest 没有加载 hooks。

## 3. 检查输出与复制

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

## 4. 可选：运行测试

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

## 5. 更新或卸载

`git pull` 后，移除再安装插件以刷新缓存，并重新检查 hook 信任。

```sh
codex plugin remove nextprompt@codex-prompty
codex plugin add nextprompt@codex-prompty
```

彻底卸载时再运行 `codex plugin marketplace remove codex-prompty`。
如需删除配置，只删除本插件的
`$CODEX_HOME/plugins/data/nextprompt-codex-prompty`；默认 `CODEX_HOME` 为
`~/.codex`。不要删除整个 Codex home 或项目目录。
