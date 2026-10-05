# Contributing

Use Python 3.9+ and a feature branch. Runtime dependencies must remain standard
library only unless a concrete portability or security need justifies an addition.

```sh
python -m pip install -e '.[dev]'
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

## Testing on each platform

CI runs on GitHub-hosted runners, which are free for public repositories, on every PR
and every push to `main`:

- **Linux**: `ubuntu-latest`, Python 3.9 to 3.14.
- **Windows**: `windows-latest`, Python 3.9 and 3.14. This is where
  `tests/test_windows_install.py` runs; check it is not skipped.
- **macOS**: `macos-latest`, Python 3.9 and 3.14. Check that
  `tests/test_unix_install.py` runs and is not skipped.

To run the Windows installer tests locally, set `PSExecutionPolicyPreference=Bypass` for
that process; the default execution policy blocks the test scripts.

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
