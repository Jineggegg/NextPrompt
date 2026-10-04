import pytest

from nextprompt.suggestion import obvious_repeat, sanitize, word_count
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
        "認証テストを実行して",
        "로그인 테스트 실행",
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


def test_inline_code_markers_are_removed_not_rejected():
    assert sanitize("Rename `foo` to `bar` in config.py.") == "Rename foo to bar in config.py."


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("建议：运行全部测试", "运行全部测试"),
        ("下一步：合并到主分支。", "合并到主分支。"),
        ("「認証テストを実行して」", "認証テストを実行して"),
    ],
)
def test_localized_prefixes_and_quotes(raw, expected):
    assert sanitize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "Continúa.",
        "Lance les tests.",
        "続けてください。",
        "계속 진행해 주세요.",
        "繼續工作",
        "我会运行回归测试。",
        "以下是下一步建议：运行测试。",
    ],
)
def test_generic_or_assistant_voice_discarded_across_languages(raw):
    assert sanitize(raw) is None


def test_word_limit_applies_to_unspaced_scripts():
    assert word_count("运行完整测试并检查最终 diff。") == 7
    assert word_count("ทดสอบระบบทั้งหมดอีกครั้ง") == 6
    assert sanitize("检" * 40) == "检" * 40
    assert sanitize("检" * 41) is None
    assert sanitize("ทดสอบระบบทั้งหมดอีกครั้ง") == "ทดสอบระบบทั้งหมดอีกครั้ง"


@pytest.mark.parametrize(
    ("completed", "proposed", "repeat"),
    [
        ("全量回归测试已全部通过，分支干净。", "运行完整回归测试，检查最终改动。", True),
        ("完整实现了登录功能，单元测试通过。", "运行完整回归测试，检查最终改动。", False),
        ("回归测试还没通过，有两个失败。", "重新运行回归测试并修复失败用例。", False),
        ("回歸測試已全部通過。", "重新執行回歸測試並檢查最終差異。", True),
        ("PR #12 已创建，CI 正在运行。", "检查 CI 结果并修复失败项。", False),
        ("PR #12 已创建，CI 正在运行。", "创建 PR 并写好说明。", True),
        ("CI 已经全部通过。", "检查 CI 结果并修复失败项。", True),
        ("CI 尚未通过。", "检查 CI 结果并修复失败项。", False),
        ("PR を作成しました。", "PR を作成して説明を書いてください", True),
        ("전체 테스트가 모두 통과했습니다.", "전체 테스트를 다시 실행해 주세요", True),
        ("전체 테스트가 통과하지 못했습니다.", "전체 테스트를 다시 실행해 주세요", False),
    ],
)
def test_completed_work_guard_multilingual(completed, proposed, repeat):
    assert obvious_repeat(proposed, [Message("assistant", completed)]) is repeat
