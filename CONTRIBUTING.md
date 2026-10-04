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

CI runs Linux only, on AJ's self-hosted runner (Python 3.9 to 3.14), because
GitHub-hosted runners stop when the account's Actions minutes run out. Until hosted
minutes are available again, every PR is tested on all three platforms like this:

- **Linux**: CI on AJ's self-hosted runner, automatic on every push.
- **Windows**: run the commands above on Songoat's Windows laptop (a fresh clone of the
  PR branch in a temporary folder). This is the only place `tests/test_windows_install.py`
  runs; check it is not skipped.
- **macOS**: Songoat runs the same commands on their own Mac.

Record the Windows and macOS results (OS, Python version, commit, pass/fail counts) in a
PR comment before merging.

在 GitHub 没有 Actions 额度时，按以下方式测试：Linux 由 AJ 的自建服务器自动跑 CI；
Windows 在 Songoat 的 Windows 笔记本上本地跑；macOS 由 Songoat 在自己的 Mac 上跑。
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
