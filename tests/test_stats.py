import json
from unittest.mock import Mock

import pytest

from nextprompt import stats
from nextprompt.cli import main, status
from nextprompt.config import ConfigStore
from nextprompt.hook import handle_context, handle_stop

STOP = {"hook_event_name": "Stop", "stop_hook_active": False, "session_id": "s1"}
PROMPT = {"hook_event_name": "UserPromptSubmit", "session_id": "s1"}


def stop(store, reply, session="s1"):
    payload = {**STOP, "session_id": session, "last_assistant_message": reply}
    handle_stop(payload, store=store, provider=Mock(), clipboard=Mock())


def send(store, prompt, session="s1"):
    handle_context({**PROMPT, "session_id": session, "prompt": prompt}, store=store)


def counts(store):
    data = json.loads((store.root / stats.STATS_NAME).read_text(encoding="utf-8"))
    return {key: data[key] for key in stats.COUNTS}


@pytest.fixture
def store(tmp_path):
    return ConfigStore(tmp_path)


SUGGESTION = "第一章写好了。\n\n→ 要不要「接着写第二章」？"


@pytest.mark.parametrize(
    "prompt, outcome",
    [
        ("接着写第二章", "exact"),
        ("接着写第二章，做吧", "exact"),  # pasted from the clipboard
        ("接着写第二章，来吧", "exact"),
        ("接着写第二章，动手吧，这次多一点对话", "extended"),
        ("接着写第二章。", "exact"),
        (stats._norm("接着写第二章") + "", "exact"),
        ("接着写第二章，这次多一点对话", "extended"),
        ("第二章先不写了，改一下标题", "ignored"),
    ],
)
def test_next_prompt_settles_the_suggestion(store, prompt, outcome):
    stop(store, SUGGESTION)
    send(store, prompt)
    result = counts(store)
    assert result["replies"] == 1 and result["suggested"] == 1
    assert result[outcome] == 1
    assert sum(result[key] for key in ("exact", "extended", "ignored")) == 1


def test_replies_without_a_line_are_counted_but_never_settled(store):
    stop(store, "已确认，PDF 收录了全部提示词和回答。")
    send(store, "谢谢")
    result = counts(store)
    assert result == {"replies": 1, "suggested": 0, "exact": 0, "extended": 0, "ignored": 0}


def test_question_replies_count_as_no_suggestion(store):
    stop(store, "封面有两个版本，你想用哪个？\n\n→ 要不要「用第一版继续」？")
    assert counts(store)["suggested"] == 0


def test_sessions_are_matched_separately(store):
    stop(store, SUGGESTION, session="a")
    stop(store, "→ Want me to “write the API section next”?", session="b")
    send(store, "write the API section next", session="b")
    send(store, "改一下标题", session="a")
    result = counts(store)
    assert result["exact"] == 1 and result["ignored"] == 1


def test_only_counts_and_hashes_are_stored(store):
    stop(store, SUGGESTION)
    raw = (store.root / stats.STATS_NAME).read_text(encoding="utf-8")
    assert "第二章" not in raw and "接着" not in raw
    pending = json.loads(raw)["pending"]["s1"]
    assert set(pending) == {"core", "length", "time"}


def test_turned_off_records_nothing(store):
    store.update(lambda cfg: cfg.update(stats=False))
    stop(store, SUGGESTION)
    send(store, "接着写第二章")
    assert not (store.root / stats.STATS_NAME).exists()


def test_broken_or_foreign_files_are_replaced(store):
    (store.root).mkdir(parents=True, exist_ok=True)
    (store.root / stats.STATS_NAME).write_text('{"replies": "x", "pending": []}', encoding="utf-8")
    stop(store, SUGGESTION)
    send(store, "接着写第二章")
    assert counts(store)["exact"] == 1


def test_pending_suggestions_are_capped(store):
    for n in range(stats.MAX_PENDING + 10):
        stop(store, SUGGESTION, session=f"s{n}")
    data = json.loads((store.root / stats.STATS_NAME).read_text(encoding="utf-8"))
    assert len(data["pending"]) == stats.MAX_PENDING


def test_status_shows_the_counts(store):
    stop(store, SUGGESTION)
    send(store, "接着写第二章，做吧")
    stop(store, "第二章写好了。\n\n→ 还差一步，「写第三章」就齐了。")
    send(store, "先改标题")
    stop(store, "标题改好了。")
    text = status(store.load(), store.root)
    assert "Stats:            On (local counts only, no text)" in text
    assert "Suggestions:      2 of 3 replies (67%)" in text
    assert "Used:             1 of 2 answered (50%): 1 as is, 0 with more words, 1 not used" in text


def test_setup_turns_stats_off_and_resets(store, capsys):
    stop(store, SUGGESTION)
    assert main(["--data-dir", str(store.root), "setup", "--stats", "reset"]) == 0
    assert not (store.root / stats.STATS_NAME).exists()
    assert "Suggestions:      0 of 0 replies" in capsys.readouterr().out
    assert main(["--data-dir", str(store.root), "setup", "--stats", "off"]) == 0
    assert store.load()["stats"] is False
    assert "Stats:            Off" in capsys.readouterr().out
