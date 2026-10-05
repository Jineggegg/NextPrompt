# Contributing

Use Python 3.9+ and a feature branch. Runtime dependencies must remain standard
library only unless a concrete portability or security need justifies an addition.

```sh
python -m pip install -e '[dev]'
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

## Testing on each platform / 各平台怎么测

GitHub Actions runs the Linux test suite on GitHub-hosted `ubuntu-latest`
runners for Python 3.9 through 3.14. The workflow runs on pushes and pull
requests. Windows and macOS are not covered by this workflow; contributors
should run the commands above on those platforms when available.

GitHub Actions 会在 GitHub 托管的 `ubuntu-latest` runner 上，对 Python 3.9 至
3.14 自动运行 Linux 测试。工作流会在推送和 Pull Request 时运行。此工作流不覆盖
Windows 和 macOS；条件允许时，请在这两个平台上运行上述命令。

Before merging, record any additional Windows and macOS results (OS, Python
version, commit, pass/fail counts) in the pull request.

合并前，请在 Pull Request 中记录额外的 Windows 和 macOS 测试结果（系统、Python
版本、提交、通过/失败数量）。

Run the opt-in real CLI suite on POSIX with Codex installed:

```sh
NEXTPROMPT_RUN_CLI_INTEGRATION=1 python -m pytest -q
```

This uses a local simulated Responses service and a disposable Codex home. On a
desktop machine the first-run Hook case copies one synthetic suggestion to your real
clipboard and may show one notification, because both are on by default. It does
not prove account access or cost. For real platform clipboard validation, record
OS/backend versions, test exact English/Chinese/emoji/multiline round trips, and
restore the previous clipboard if safe. Mark only actually verified machines Tested.

Before changing integration contracts, inspect current CLI help, official docs
and source; update docs/RESEARCH.md and integration evidence. Never patch Codex,
simulate UI buttons, execute predicted prompts or loosen recursion guards.
Protect the config/transcript/provider boundary with meaningful tests. Keep
modules small and typed, use unique temporary paths and atomic settings updates.

Never commit real credentials, transcripts, captured contexts or raw error dumps.
Use obvious fake fixtures. Report vulnerabilities according to SECURITY.md.
PR descriptions should explain the concrete resulting behavior, tests and limits.
Use Semantic Versioning and clear conventional commits. Do not merge or publish a
release until review is complete.
