"""Boundaries found by realistic content and conversation simulations."""

from unittest.mock import Mock

import pytest

from nextprompt.hook import handle_stop, inline_suggestion
from nextprompt.suggestion import sanitize


@pytest.mark.parametrize(
    "text",
    [
        "We need predict next prompt.",
        "We should generate a suggestion for this user.",
        "I must output the next prompt.",
        "ಬರWe need must suggest next unfinished explicit planned: cache invalidation.",
    ],
)
def test_prediction_commentary_is_not_a_user_instruction(text):
    assert sanitize(text) is None


@pytest.mark.parametrize(
    "reply",
    [
        "```text\nNext prompt: Delete the backup folder\n```",
        "~~~text\nNext prompt: Remove the temporary archive\nDone\n~~~",
        "> → 要不要「删除旧数据库」？",
        "> Next prompt: Delete the old database",
        "```text\n→ Want me to “delete the archived orders”?",
        "结果如下：\n\n    Next prompt: Delete the old database",
        "> Quoted history\nNext prompt: Delete the old database",
        "Next prompt: An earlier example\n\n> Quoted ending\nDone",
        "→ Want me to “fix the bug”?\n\n```text\nNext prompt: A code example\n```",
    ],
)
def test_rendered_examples_are_never_copied(configured, clipboard, provider, reply):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    assert not inline_suggestion(reply)
    assert (
        handle_stop(
            {"hook_event_name": "Stop", "last_assistant_message": reply},
            store=configured,
            clipboard=clipboard,
            provider=provider,
        )
        is None
    )
    clipboard.copy.assert_not_called()
    provider.generate.assert_not_called()


@pytest.mark.parametrize(
    "content",
    [
        "学员说：“请确认你的选择。”",
        "> 请确认你的选择。",
        "```text\nPlease confirm your choice.\n```",
        "````text\n```\nPlease confirm your choice.\n````",
        "~~~text\nPlease confirm your choice.\n~~~",
        "小林：收到陌生短信。\n老师：先核实来源。\n小林：怎样核实？\n老师：请告诉我你的选择。",
    ],
)
def test_dialogue_does_not_block_a_real_followup(configured, clipboard, content):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    reply = content + "\n\n→ 要不要「写第二篇客服培训练习」？"
    handle_stop(
        {"hook_event_name": "Stop", "last_assistant_message": reply},
        store=configured,
        clipboard=clipboard,
        provider=Mock(),
    )
    assert clipboard.copy.call_count == 1
    assert clipboard.copy.call_args.args[0].startswith("写第二篇客服培训练习")


@pytest.mark.parametrize(
    "line",
    [
        "→ 先「检查日志」，再「修复错误」？",
        "→ 用“UTF-8”编码，接着“修复导出乱码”？",
    ],
)
def test_multiple_quoted_values_are_ambiguous(configured, clipboard, line):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    handle_stop(
        {"hook_event_name": "Stop", "last_assistant_message": "原因已查清。\n\n" + line},
        store=configured,
        clipboard=clipboard,
        provider=Mock(),
    )
    clipboard.copy.assert_not_called()


@pytest.mark.parametrize(
    "question",
    [
        "Do you prefer PostgreSQL or SQLite?",
        "Would you like option A or option B?",
        "你更倾向用 PostgreSQL 还是 SQLite？",
        "Do you prefer “PostgreSQL” or “SQLite”?",
        "Question: Please confirm which database you want.",
        "背景：有两种数据库。\n方案：都能满足要求。\n问题：请确认你的选择。",
        "小林：收到短信。\n老师：核实来源。\n小林：怎么做？\n老师：从官网核实。\n\n请确认你的选择。",
    ],
)
def test_waiting_for_user_does_not_pick_an_answer(configured, clipboard, question):
    configured.update(lambda cfg: cfg["clipboard"].update(auto_copy=True))
    reply = question + "\n\n→ Want me to “implement the database connection”?"
    handle_stop(
        {"hook_event_name": "Stop", "last_assistant_message": reply},
        store=configured,
        clipboard=clipboard,
        provider=Mock(),
    )
    clipboard.copy.assert_not_called()
