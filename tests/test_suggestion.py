import pytest

from nextprompt.suggestion import obvious_repeat, sanitize
from nextprompt.transcript import Message

PROMPT = "Run the full regression suite and review the final diff."


@pytest.mark.parametrize(
    "raw",
    [
        PROMPT,
        f'"{PROMPT}"',
        f"Suggestion: {PROMPT}",
        f"Next: {PROMPT}",
        f"Next prompt: {PROMPT}",
        f"Prompt: {PROMPT}",
        f"```text\n{PROMPT}\n```",
        f"{PROMPT} Create a pull request.",
        f"1. {PROMPT}\n2. Create a pull request.",
        f"- {PROMPT}",
    ],
)
def test_normalization(raw):
    assert sanitize(raw) == PROMPT


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "???",
        "Continue.",
        "Keep working.",
        "Proceed.",
        "Check your work.",
        "Do more testing.",
        "Fix the issue.",
        "Yes.",
        "null",
        "{}",
        "word " * 21,
        "a" * 241,
        "Run tests.\x1b]52;c;malicious",
        "Review\u202e dangerous changes.",
        "Use sk-test-example-not-real for authentication.",
        "I will run the regression tests.",
        "Here is the next prompt: Run regression tests.",
        "Visit https://example.com now.",
    ],
)
def test_discard_invalid(raw):
    assert sanitize(raw) is None


@pytest.mark.parametrize(
    "text",
    [
        "运行完整测试并检查最终 diff。",
        "检查 CI 后创建 PR。",
        "Review the 🚀 release diff.",
        "运行全部测试",
        "合并到主分支",
        "テストを実行して",
        "테스트 실행",
    ],
)
def test_unicode_suggestion(text):
    assert sanitize(text) == text


@pytest.mark.parametrize("text", ["继续", "继续工作。", "修复问题", "好的。", "Run it."])
def test_short_or_generic_discarded_in_any_language(text):
    assert sanitize(text) is None


@pytest.mark.parametrize(
    ("completed", "proposed", "repeat"),
    [
        ("Implemented the fix. Targeted tests pass.", PROMPT, False),
        ("Full regression passed and the branch is clean.", PROMPT, True),
        (
            "PR #54 was created and CI is currently running.",
            "Check the CI results and fix any failures before merging.",
            False,
        ),
        (
            "PR #54 was created.",
            "Create the pull request and summarize the changes for review.",
            True,
        ),
    ],
)
def test_completed_work_guard(completed, proposed, repeat):
    assert obvious_repeat(proposed, [Message("assistant", completed)]) is repeat
