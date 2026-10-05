# Contributing

Use Python 3.9+ and a feature branch. Runtime dependencies must remain standard
library only unless a concrete portability or security need justifies an addition.

```sh
python -m pip install -e '.[dev]'
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

## Testing on each platform / 各平台怎么测

CI runs Linux only, on a GitHub-hosted `ubuntu-latest` runner (Python 3.9 to 3.14).
Windows and macOS are not in CI yet, so every PR is tested on all three platforms like this:

- **Linux**: CI on GitHub-hosted `ubuntu-latest`, automatic on every push and PR.
- **Windows**: run the commands above locally on Songoat's Windows laptop (a fresh clone
  of the PR branch in a temporary folder). This is the only place
  `tests/test_windows_install.py` runs; check it is not skipped.
- **macOS**: Claude runs the same commands on Songoat's Mac, reached over Tailscale from
  the Windows laptop (SSH), again in a fresh clone in a temporary folder. Check that
  `tests/test_unix_install.py` runs and is not skipped.

Record the Windows and macOS results (OS, Python version, commit, pass/fail counts) in a
PR comment before merging.

按以下方式测试：Linux 由 GitHub 托管的 `ubuntu-latest` 自动跑 CI；
Windows 在 Songoat 的 Windows 笔记本上本地跑；macOS 由 Claude 通过 Tailscale（从 Windows
笔记本 SSH）连到 Songoat 的 Mac 上跑。Windows 和 macOS 都用临时文件夹里的全新克隆。
合并前把 Windows 和 macOS 的结果（系统、Python 版本、提交、通过/失败数量）写在 PR 评论里。

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
