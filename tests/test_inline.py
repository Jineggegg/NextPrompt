import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from nextprompt.config import ConfigError, ConfigStore
from nextprompt.hook import (
    INLINE_PATH,
    INLINE_REMINDER,
    STYLE_HINTS,
    WELCOME_MARKER,
    asks_user,
    handle_context,
    handle_stop,
    inline_reminder,
    inline_suggestion,
)
from nextprompt.i18n import GO_AHEAD, INLINE_LABELS, go_ahead
from nextprompt.transcript import Message

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = {"hook_event_name": "Stop", "transcript_path": "/fake/session", "stop_hook_active": False}
START = {"hook_event_name": "SessionStart", "source": "startup", "session_id": "s"}
PROMPT = {"hook_event_name": "UserPromptSubmit", "prompt": "fix it", "session_id": "s"}


def reply(last_line):
    return f"Fixed the redirect and the targeted tests pass.\n\n{last_line}"


def test_source_defaults_to_inline_and_validates(tmp_path):
    store = ConfigStore(tmp_path)
    assert store.load()["source"] == "inline"
    with pytest.raises(ConfigError):
        store.update(lambda cfg: cfg.update(source="root"))


def test_context_injects_instruction_and_reminder_by_default(configured):
    text = handle_context(START, store=configured)
    assert text == INLINE_PATH.read_text(encoding="utf-8").strip()
    assert "→ " in text and "「" in text and "“" in text
    assert handle_context(PROMPT, store=configured).startswith(INLINE_REMINDER)


@pytest.mark.parametrize(
    "change",
    [
        lambda cfg: cfg.update(enabled=False),
        lambda cfg: cfg.update(trigger_mode="manual"),
        lambda cfg: cfg.update(source="model"),
    ],
)
def test_context_silent_when_off_or_model_mode(configured, change):
    configured.update(change)
    assert handle_context(START, store=configured) is None
    assert handle_context(PROMPT, store=configured) is None


def test_context_ignores_internal_runs_and_other_events(configured, monkeypatch):
    assert handle_context({**START, "hook_event_name": "Stop"}, store=configured) is None
    assert handle_context("not a dict", store=configured) is None
    monkeypatch.setenv("NEXTPROMPT_INTERNAL", "1")
    assert handle_context(START, store=configured) is None


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Next prompt: Add a regression test for logout.", "Add a regression test for logout."),
        ("**Next prompt:** Add a logout test", "Add a logout test"),
        ("下一步建议：运行完整回归测试，检查最终改动。", "运行完整回归测试，检查最终改动。"),
        ("**下一步建议：** `pytest -q`", "pytest -q"),
        # Copied as written: generic or multi-sentence text is not rewritten.
        ("下一步建议：继续", "继续"),
        ("Next prompt: Merge it. Then tag the release.", "Merge it. Then tag the release."),
    ],
)
def test_extracts_the_visible_text(line, expected):
    assert inline_suggestion(reply(line)) == expected


@pytest.mark.parametrize("text", [None, "", "All done, nothing else to do."])
def test_no_line(text):
    assert inline_suggestion(text) is None


UNSAFE = [
    "Next prompt: rotate sk-abcdefghijklmnopqrstuvwxyz0123456789 now",
    "Next prompt: bad \x1b[31m escape",
    "Next prompt: " + "x" * 501,
    "Next prompt: **",
]


@pytest.mark.parametrize("text", UNSAFE)
def test_unsafe_or_empty_lines_are_not_copied(text):
    assert inline_suggestion(text) == ""


@pytest.mark.parametrize("text", UNSAFE)
def test_unsafe_line_never_copies_a_different_prompt(configured, provider, clipboard, text):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    payload = {**PAYLOAD, "last_assistant_message": text}
    assert handle_stop(payload, store=configured, provider=provider, clipboard=clipboard) is None
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


def test_only_the_end_of_the_reply_counts():
    text = "Next prompt: Add a regression test for logout.\n" + "\n".join(["more"] * 5)
    assert inline_suggestion(text) is None


MEMORY_FOOTER = """
<oai-mem-citation>
<citation_entries>
MEMORY.md:1-1|note=[synthetic test]
</citation_entries>
<rollout_ids>
</rollout_ids>
</oai-mem-citation>
"""


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize(
    "last, expected",
    [
        (
            "第一节已写好，第二节还没写。\n\n→ 还差一步，「接着写第二节」就齐了。",
            "接着写第二节",
        ),
        (
            "Found the export failure; the fix is still pending.\n\n"
            "→ One loose end: “fix the export failure”.",
            "fix the export failure",
        ),
        (
            "术语已解释，之前的导出修复还没完成。\n\n→ 可以接着「完成导出修复」。",
            "完成导出修复",
        ),
    ],
)
def test_hidden_memory_footer_preserves_visible_suggestion(
    configured, clipboard, notifications, provider, newline, last, expected
):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = (last + MEMORY_FOOTER + " \t\n").replace("\n", newline)
    assert inline_suggestion(last) == expected
    text = handle_stop(
        {**PAYLOAD, "last_assistant_message": last},
        store=configured,
        provider=provider,
        clipboard=clipboard,
    )
    clipboard.copy.assert_called_once_with(go_ahead(expected))
    provider.generate.assert_not_called()
    notifications.assert_called_once()
    assert text in ("✓ 已复制到剪贴板", "✓ Copied to clipboard")


@pytest.mark.parametrize("suggestion", ["", "\n\n→ 要不要「执行下一步」？"])
@pytest.mark.parametrize("body", ["请确认是否执行下一步。", "Which branch should I target?"])
def test_hidden_memory_footer_keeps_confirmation_guard(
    configured, clipboard, provider, suggestion, body
):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = body + suggestion + MEMORY_FOOTER
    assert asks_user(last)
    assert (
        handle_stop(
            {**PAYLOAD, "last_assistant_message": last},
            store=configured,
            provider=provider,
            clipboard=clipboard,
        )
        is None
    )
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


@pytest.mark.parametrize(
    "suffix",
    [
        "\n正文还没有结束。",
        MEMORY_FOOTER + "正文还没有结束。",
        "\n```xml" + MEMORY_FOOTER + "\n```",
        "\n```xml" + MEMORY_FOOTER,
        "\n" + "\n".join("> " + line for line in MEMORY_FOOTER.splitlines()),
        "\n" + "\n".join("    " + line for line in MEMORY_FOOTER.splitlines()),
        MEMORY_FOOTER.replace("</oai-mem-citation>", ""),
    ],
)
def test_visible_or_incomplete_footer_does_not_move_a_suggestion_to_the_end(suffix):
    last = "第一节已写好。\n\n→ 还差一步，「接着写第二节」就齐了。" + suffix
    assert inline_suggestion(last) is None


def test_inline_stop_copies_the_quoted_prompt_as_a_go_ahead(configured, clipboard, notifications):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    provider = Mock()
    last = reply("→ 要不要顺手「给登出流程加一个回归测试」？")
    payload = {**PAYLOAD, "last_assistant_message": last}
    text = handle_stop(payload, store=configured, provider=provider, clipboard=clipboard)
    provider.generate.assert_not_called()
    copied = go_ahead("给登出流程加一个回归测试")
    assert copied.startswith("给登出流程加一个回归测试，")
    clipboard.copy.assert_called_once_with(copied)
    # The reply already shows the prompt, so only the copy status is added.
    assert text == "✓ 已复制到剪贴板"
    notifications.assert_called_once_with("下一句已复制", copied)


def test_inline_display_only_adds_nothing(configured, clipboard):
    payload = {**PAYLOAD, "last_assistant_message": reply("Next prompt: Add a logout test.")}
    assert handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard) is None
    clipboard.copy.assert_not_called()


def test_reply_without_a_line_suggests_nothing(configured, provider, clipboard):
    # Leaving the line out is the model's decision that no next step is worth it.
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    payload = {**PAYLOAD, "last_assistant_message": "PDF 已生成，共 14 页。"}
    text = handle_stop(
        payload,
        store=configured,
        conversation=Mock(read=Mock(return_value=[Message("user", "确保有提示词和回答")])),
        provider=provider,
        clipboard=clipboard,
    )
    assert text is None
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


def test_inline_falls_back_to_the_model_without_the_reply_text(configured, provider, clipboard):
    payload = dict(PAYLOAD)
    text = handle_stop(
        payload,
        store=configured,
        conversation=Mock(read=Mock(return_value=[Message("user", "Fix the login redirect.")])),
        provider=provider,
        clipboard=clipboard,
    )
    provider.generate.assert_called_once()
    assert text == "Next prompt:\nRun the full regression suite and review the final diff."


def run_context(tmp_path, payload):
    return subprocess.run(
        [sys.executable, str(ROOT / "hooks/context.py")],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env={**os.environ, "PLUGIN_DATA": str(tmp_path)},
        timeout=5,
    )


def test_context_entrypoint_shows_onboarding_once_and_keeps_inline_context(tmp_path):
    start = run_context(tmp_path, START)
    assert start.returncode == 0
    first = json.loads(start.stdout)
    assert "NextPrompt 已加载" in first["systemMessage"]
    assert "自动复制到剪贴板 / auto-copy 开 / on" in first["systemMessage"]
    assert "桌面通知 / desktop notification 开 / on" in first["systemMessage"]
    assert "$nextprompt-setup" in first["systemMessage"]
    assert first["hookSpecificOutput"] == {
        "hookEventName": "SessionStart",
        "additionalContext": INLINE_PATH.read_text(encoding="utf-8").strip(),
    }
    assert (tmp_path / WELCOME_MARKER).exists()
    # Later SessionStart runs continue to inject context without repeating the report.
    resumed = run_context(tmp_path, {**START, "source": "resume"})
    assert resumed.stdout.decode("utf-8").startswith("NextPrompt is installed.")
    prompt = run_context(tmp_path, PROMPT)
    assert prompt.returncode == 0
    assert prompt.stdout.decode("utf-8").strip().startswith(INLINE_REMINDER)


def test_context_entrypoint_silent_in_model_mode(tmp_path):
    ConfigStore(tmp_path).update(lambda cfg: cfg.update(source="model"))
    result = run_context(tmp_path, START)
    assert "NextPrompt 已加载" in json.loads(result.stdout)["systemMessage"]
    assert "hookSpecificOutput" not in json.loads(result.stdout)
    result = run_context(tmp_path, {**START, "source": "resume"})
    assert result.returncode == 0 and result.stdout == b""


def test_onboarding_reports_saved_preferences(tmp_path):
    ConfigStore(tmp_path).update(
        lambda cfg: (cfg["clipboard"].update(auto_copy=False), cfg.update(notify=False))
    )
    report = json.loads(run_context(tmp_path, START).stdout)["systemMessage"]
    assert "自动复制到剪贴板 / auto-copy 关 / off" in report
    assert "桌面通知 / desktop notification 关 / off" in report
    assert "默认均开启 / both on by default" in report


def test_disabled_plugin_does_not_show_onboarding(tmp_path):
    ConfigStore(tmp_path).update(lambda cfg: cfg.update(enabled=False))
    assert run_context(tmp_path, START).stdout == b""
    assert not (tmp_path / WELCOME_MARKER).exists()


def test_shipped_hooks_cover_all_three_events():
    hooks = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert list(hooks) == ["SessionStart", "UserPromptSubmit", "Stop"]
    for event in ("SessionStart", "UserPromptSubmit"):
        assert "context.py" in hooks[event][0]["hooks"][0]["command"]


@pytest.mark.parametrize("language, label", sorted(INLINE_LABELS.items()))
def test_earlier_language_labels_are_still_parsed(language, label):
    sep = "" if label.endswith("：") else " "
    assert inline_suggestion(reply(f"{label}{sep}Texto 提示 テスト")) == "Texto 提示 テスト"


@pytest.mark.parametrize(
    "line, expected",
    [
        ("次のプロンプト：ログアウトの回帰テストを追加して", "ログアウトの回帰テストを追加して"),
        ("다음 프롬프트: 로그아웃 회귀 테스트를 추가해 줘", "로그아웃 회귀 테스트를 추가해 줘"),
        (
            "Prochain prompt : Ajoute un test pour la déconnexion",
            "Ajoute un test pour la déconnexion",
        ),
        ("**Nächster Prompt:** Füge einen Logout-Test hinzu", "Füge einen Logout-Test hinzu"),
        ("下一步建議：替登出流程加上回歸測試", "替登出流程加上回歸測試"),
    ],
)
def test_localized_lines_copy_the_visible_text(line, expected):
    assert inline_suggestion(reply(line)) == expected


def test_localized_line_reports_in_that_language(configured, clipboard):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = reply("次のプロンプト：ログアウトの回帰テストを追加して")
    payload = {**PAYLOAD, "last_assistant_message": last}
    text = handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard)
    clipboard.copy.assert_called_once_with("ログアウトの回帰テストを追加して")
    assert text == "✓ クリップボードにコピーしました"


# The reported loop: the assistant asks which task to do, the suggestion asks it back.
QUESTION = "好的，我们一步一步来。你想先做哪个任务？"


@pytest.mark.parametrize(
    "last",
    [
        QUESTION + "\n\n下一步建议：下一步该做什么任务",
        QUESTION,  # no line: the fallback model must not run either
        "Done with step one.\nWhich option would you like: A or B?\n\nNext prompt: Pick option A",
        "需要你确认一下。\n请告诉我要部署到哪个环境。",
        "Before I start, please confirm the target branch.",
    ],
)
def test_question_replies_copy_nothing_and_skip_the_fallback(configured, provider, clipboard, last):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    payload = {**PAYLOAD, "last_assistant_message": last}
    text = handle_stop(
        payload,
        store=configured,
        conversation=Mock(read=Mock(return_value=[Message("user", "帮我做个小任务")])),
        provider=provider,
        clipboard=clipboard,
    )
    assert text is None
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


def test_question_rule_applies_in_model_mode_too(configured, provider, clipboard):
    configured.update(lambda cfg: cfg.update(source="model"))
    payload = {**PAYLOAD, "last_assistant_message": QUESTION}
    assert handle_stop(payload, store=configured, provider=provider, clipboard=clipboard) is None
    provider.generate.assert_not_called()


@pytest.mark.parametrize(
    "line",
    [
        "下一步建议：下一步该做什么任务",
        "下一步建议：接下来做什么",
        "下一步建议：有什么建议",
        "下一步建议：继续",
        "Next prompt: What should I do next?",
        "Next prompt: what's next",
        "次のプロンプト：次は何をすればいい？",
    ],
)
def test_decision_returning_lines_are_not_copied(configured, provider, clipboard, line):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    payload = {**PAYLOAD, "last_assistant_message": reply(line)}
    assert handle_stop(payload, store=configured, provider=provider, clipboard=clipboard) is None
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


@pytest.mark.parametrize(
    "line, expected",
    [
        # A suggestion that is itself a question is still the user's to ask.
        ("下一步建议：为什么登录测试会失败？", "为什么登录测试会失败？"),
        ("Next prompt: Explain what this function does", "Explain what this function does"),
        ("下一步建议：解释一下这个函数做什么", go_ahead("解释一下这个函数做什么")),
        ("→ 想追查的话：「为什么登录测试会失败？」", "为什么登录测试会失败？"),
    ],
)
def test_concrete_prompts_still_copy(configured, clipboard, line, expected):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    payload = {**PAYLOAD, "last_assistant_message": reply(line)}
    handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard)
    clipboard.copy.assert_called_once_with(expected)


def test_instructions_cover_questions_typos_and_loops():
    inline = INLINE_PATH.read_text(encoding="utf-8")
    assert "asks the user a question" in inline and "write no suggestion" in inline
    assert "typos fixed" in inline and "three kinds of step" in inline
    assert "Write no line for a new idea" in inline
    assert "下一步该做什么任务" in inline
    assert "Omit the line when this reply asks the user a question" in INLINE_REMINDER


@pytest.mark.parametrize(
    "line, expected",
    [
        ("→ 要不要「给 PDF 加上目录和页码」？", "给 PDF 加上目录和页码"),
        ("→ 顺手的话，可以「把简介压到 100 字以内」。", "把简介压到 100 字以内"),
        ("→ 「把四章合成一个 EPUB」，需要就说一声。", "把四章合成一个 EPUB"),
        ("**→ 还差最后一块：「补上第三章的结尾」**", "补上第三章的结尾"),
        ("→ Want me to “add a regression test for logout”?", "add a regression test for logout"),
        ('-> One loose end: "update the README for the flag".', "update the README for the flag"),
        ("→ 次は「回帰テストを追加して」はいかが？", "回帰テストを追加して"),
        ("→ 要不要「`pytest -q`」跑一遍？", "pytest -q"),
    ],
)
def test_suggestion_line_copies_only_the_quoted_prompt(line, expected):
    assert inline_suggestion(reply(line)) == expected


@pytest.mark.parametrize(
    "text",
    [
        # Quotes in an ordinary closing sentence are not a suggestion.
        "已把标题改成「雾中邮局」。",
        'Renamed the flag to "--dry-run".',
        # The suggestion line must be the last line.
        "→ 要不要「给 PDF 加目录」？\n另外，封面也已经更新。",
    ],
)
def test_quotes_outside_a_final_suggestion_line_are_ignored(text):
    assert inline_suggestion(text) is None


def test_arrow_line_without_a_quoted_prompt_copies_nothing(configured, provider, clipboard):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = reply("→ 要不要把目录和页码也加上")
    assert inline_suggestion(last) == ""
    payload = {**PAYLOAD, "last_assistant_message": last}
    assert handle_stop(payload, store=configured, provider=provider, clipboard=clipboard) is None
    provider.generate.assert_not_called()
    clipboard.copy.assert_not_called()


def test_question_shaped_suggestion_is_not_a_question_to_answer(configured, clipboard):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = "PDF 已经生成，共 14 页。\n\n→ 要不要「给 PDF 加上目录」？"
    payload = {**PAYLOAD, "last_assistant_message": last}
    handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard)
    clipboard.copy.assert_called_once_with(go_ahead("给 PDF 加上目录"))


def test_reply_that_asks_first_copies_nothing_even_with_a_line(configured, clipboard):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = "封面有两个版本，你想用哪个？\n\n→ 要不要「用第一版封面重新导出」？"
    payload = {**PAYLOAD, "last_assistant_message": last}
    assert handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard) is None
    clipboard.copy.assert_not_called()


@pytest.mark.parametrize(
    "prompt, core, language",
    [
        ("给 PDF 加上目录", "给 PDF 加上目录", "zh"),
        ("把简介压到 100 字以内。", "把简介压到 100 字以内", "zh"),
        ("替登出流程加上回歸測試", "替登出流程加上回歸測試", "zh-TW"),
    ],
)
def test_chinese_prompts_get_a_go_ahead(prompt, core, language):
    copied = go_ahead(prompt)
    assert copied.removeprefix(core + "，") in GO_AHEAD[language]
    assert go_ahead(prompt) == copied  # stable for the same prompt


@pytest.mark.parametrize(
    "prompt",
    [
        "为什么登录测试会失败？",
        "那就重新导出吧",
        "add a regression test for logout",
        "ログアウトの回帰テストを追加して",
    ],
)
def test_questions_finished_go_aheads_and_other_languages_stay(prompt):
    assert go_ahead(prompt) == prompt


def test_go_aheads_vary_across_prompts():
    prompts = [f"把第 {n} 章改成第一人称" for n in range(1, 13)]
    assert len({go_ahead(p).rsplit("，", 1)[1] for p in prompts}) > 1


@pytest.mark.parametrize(
    "prompt, language",
    [
        ("把第二章写完", "zh"),
        ("ログイン画面を作って", "ja"),
        ("fix the login test", "en"),
        ("로그인 테스트 고쳐 줘", "ko"),
        (None, "en"),
    ],
)
def test_reminder_proposes_a_shape_in_the_users_script(prompt, language):
    reminder = inline_reminder(prompt)
    assert reminder.startswith(INLINE_REMINDER)
    assert reminder.rsplit("→ ", 1)[1] in STYLE_HINTS[language]


def test_reminder_shapes_vary_between_turns():
    assert len({inline_reminder("把第二章写完") for _ in range(50)}) > 1


@pytest.mark.parametrize(
    "text, expected",
    [
        # Written at the end of the last paragraph instead of on its own line.
        ("CI 挂在时区断言上，没有改动文件。→ 要不要「修复这个时区测试」？", "修复这个时区测试"),
        (
            "Found the flaky wait. → Want me to “replace the sleep with an event”?",
            "replace the sleep with an event",
        ),
    ],
)
def test_suggestion_at_the_end_of_the_last_paragraph(text, expected):
    assert inline_suggestion(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        'Changed "foo" → "bar" in the config.',
        "改名：「旧标题」→「雾中邮局」",
        'Mapped the key "a" -> "b".',
    ],
)
def test_arrows_inside_ordinary_sentences_are_not_suggestions(text):
    assert inline_suggestion(text) is None


def test_question_before_a_same_line_suggestion_still_counts(configured, clipboard):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = "封面有两个版本，你想用哪个？ → 要不要「用第一版封面重新导出」？"
    payload = {**PAYLOAD, "last_assistant_message": last}
    assert handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard) is None
    clipboard.copy.assert_not_called()


@pytest.mark.parametrize(
    "text, expected",
    [
        # The arrow was dropped, but the closing line still offers one quoted step.
        (
            "第 2 节已写好。\n\n顺手的话，可以「写第 3 节：数据库与模型」。",
            "写第 3 节：数据库与模型",
        ),
        ("统计图和 CSV 导出还没做，可以「接着做统计图」。", "接着做统计图"),
        (
            "ログイン画面を作りました。\n続けて「サインアップ画面も作って」？",
            "サインアップ画面も作って",
        ),
        (
            "Added the flag.\n\nWant me to “add tests for the dry-run flag”?",
            "add tests for the dry-run flag",
        ),
    ],
)
def test_closing_offer_without_the_arrow_still_counts(text, expected):
    assert inline_suggestion(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        # Offers inside quoted dialogue belong to the story.
        "雾越来越浓。\n“要不要一起走？”她问。",
        'The fog thickened.\n"Want me to stay?" she asked.',
        # Two quotes or no offer wording: not a suggestion.
        "要不要把「标题」改成「雾中邮局」？",
        "你也可以「右键另存为」。",
    ],
)
def test_quotes_without_an_offer_of_our_own_are_not_suggestions(text):
    assert inline_suggestion(text) is None


@pytest.mark.parametrize(
    "body",
    [
        # A story or blurb that ends on a question is content, not a question to the user.
        "林晚攥紧铜铃。门外的父亲，又是谁？",
        "“你是谁？”",
        # Offering the same step in the body and in the line is still one offer.
        "登录跳转那两个失败用例还没处理完；要我接着修吗？",
    ],
)
def test_trailing_question_before_a_suggestion_still_copies(configured, clipboard, body):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = f"{body}\n\n→ 还差一步：「写第四章」。"
    payload = {**PAYLOAD, "last_assistant_message": last}
    handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard)
    clipboard.copy.assert_called_once_with(go_ahead("写第四章"))


@pytest.mark.parametrize(
    "body",
    [
        "封面有两个版本，你想用哪个？",
        "要先迁测试还是先迁构建脚本？",
        "Which branch should I target?",
        "请确认要部署到哪个环境。",
    ],
)
def test_choice_questions_before_a_suggestion_copy_nothing(configured, clipboard, body):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = f"{body}\n\n→ 要不要「用第一版继续」？"
    payload = {**PAYLOAD, "last_assistant_message": last}
    assert handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard) is None
    clipboard.copy.assert_not_called()


@pytest.mark.parametrize(
    "line, expected",
    [
        (
            "下一步可以接着做列表：「展示、筛选和删除已录入的账目」。",
            "展示、筛选和删除已录入的账目",
        ),
        (
            "要继续的话，CI 的失败原因还没修，可以「修复过期令牌返回 500 的问题」。",
            "修复过期令牌返回 500 的问题",
        ),
        ("想继续的话，说「写第三章」就行。", "写第三章"),
    ],
)
def test_more_closing_offers_without_the_arrow(line, expected):
    assert inline_suggestion(f"做好了。\n\n{line}") == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        # The offer is the last sentence of a longer closing paragraph.
        (
            "ログイン画面を作成しました。サインアップ画面はまだ未着手です。"
            "必要なら「サインアップ画面も作って」とどうぞ。",
            "サインアップ画面も作って",
        ),
        (
            "Added the flag and its help text. Want me to “add tests for the dry-run flag”?",
            "add tests for the dry-run flag",
        ),
    ],
)
def test_offer_in_the_closing_sentence_of_a_paragraph(text, expected):
    assert inline_suggestion(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "她想起父亲说过的话。“下一步，去河边。”",
        "改好了。他始终不知道「答案」。",
        "README 已更新。运行「pytest -q」即可验证。",
    ],
)
def test_closing_sentences_without_an_offer_are_not_suggestions(text):
    assert inline_suggestion(text) is None


@pytest.mark.parametrize(
    "line, expected",
    [
        ("→ 「继续写《雾中邮局》第三章》，需要就说一声。", "继续写《雾中邮局》第三章"),
        ("→ 接下来「写完《雾中邮局》第四章》，怎么样？", "写完《雾中邮局》第四章"),
        ("→ 要不要「把《雾中邮局》排成 PDF」？", "把《雾中邮局》排成 PDF"),
    ],
)
def test_book_titles_inside_the_quote(line, expected):
    assert inline_suggestion(reply(line)) == expected


def hint_of(reminder):
    return reminder.rsplit("→ ", 1)[1]


def test_shapes_rotate_within_a_session(tmp_path):
    store = ConfigStore(tmp_path)
    hints = [hint_of(inline_reminder("把第二章写完", "s1", store)) for _ in range(20)]
    # Never the same shape twice in a row, and every shape comes up.
    assert all(a != b for a, b in zip(hints, hints[1:]))
    assert set(hints) == set(STYLE_HINTS["zh"])


def test_sessions_rotate_independently_and_state_stays_small(tmp_path):
    store = ConfigStore(tmp_path)
    first = hint_of(inline_reminder("fix it", "a", store))
    for n in range(60):
        inline_reminder("fix it", f"other-{n}", store)
    state = json.loads((tmp_path / ".styles.json").read_text(encoding="utf-8"))
    assert len(state) == 50 and "a" not in state
    # Only shape positions are stored: no prompt text.
    assert all(isinstance(v, int) for v in state.values())
    assert first in STYLE_HINTS["en"]


@pytest.mark.parametrize("content", ["not json", "[1, 2]", '{"s1": "x"}'])
def test_broken_style_state_is_replaced(tmp_path, content):
    (tmp_path / ".styles.json").write_text(content, encoding="utf-8")
    store = ConfigStore(tmp_path)
    assert hint_of(inline_reminder("把第二章写完", "s1", store)) in STYLE_HINTS["zh"]
    state = json.loads((tmp_path / ".styles.json").read_text(encoding="utf-8"))
    assert isinstance(state["s1"], int)


def test_prompt_hook_uses_the_session_rotation(configured):
    payload = {**PROMPT, "prompt": "把第二章写完", "session_id": "s9"}
    hints = [hint_of(handle_context(payload, store=configured)) for _ in range(3)]
    assert len(set(hints)) == 3


def test_korean_prompts_get_korean_shapes_and_offers():
    assert hint_of(inline_reminder("로그인 화면 만들어 줘")) in STYLE_HINTS["ko"]
    text = (
        "로그인 화면을 만들었어요.\n다음으로 「회원가입 화면도 만들어 줘」를 이어서 할 수 있어요."
    )
    assert inline_suggestion(text) == "회원가입 화면도 만들어 줘"


def test_written_content_earlier_in_the_reply_does_not_block_the_copy(configured, clipboard):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    last = (
        "4. 启动前运行 `app config validate`。若提示未知字段，请确认它们是否已重命名。\n"
        "完成配置迁移后，再继续迁移 API 和 CLI。\n"
        "→ Still to do: “Continue with the API migration guide”."
    )
    payload = {**PAYLOAD, "last_assistant_message": last}
    handle_stop(payload, store=configured, provider=Mock(), clipboard=clipboard)
    clipboard.copy.assert_called_once_with("Continue with the API migration guide")


def test_onboarding_when_installed_mid_chat(tmp_path):
    first = json.loads(run_context(tmp_path, PROMPT).stdout)
    assert "NextPrompt 已加载" in first["systemMessage"]
    assert first["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert first["hookSpecificOutput"]["additionalContext"].startswith(INLINE_REMINDER)
    assert run_context(tmp_path, PROMPT).stdout.decode("utf-8").startswith(INLINE_REMINDER)
