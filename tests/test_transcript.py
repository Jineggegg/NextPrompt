import json

import pytest

from nextprompt.transcript import (
    TAIL_BYTES,
    CodexConversationAdapter,
    Message,
    bounded_messages,
    format_context,
)


def record(role, text, channel=None):
    return {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": role,
            "channel": channel,
            "content": [{"type": "input_text", "text": text}],
        },
    }


def write_records(path, records):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    return path


@pytest.mark.parametrize("count", [0, 3, 5, 20])
def test_last_five(tmp_path, settings, count):
    records = [
        record("user" if i % 2 == 0 else "assistant", f"Natural message number {i}.")
        for i in range(count)
    ]
    path = write_records(tmp_path / "session", records)
    messages = bounded_messages(CodexConversationAdapter().read(path), settings["context"])
    assert len(messages) == min(count, 5)
    assert [m.text for m in messages] == [
        f"Natural message number {i}." for i in range(max(0, count - 5), count)
    ]


def test_missing_malformed_and_empty(tmp_path):
    adapter = CodexConversationAdapter()
    assert adapter.read(tmp_path / "missing") == []
    path = tmp_path / "session"
    path.write_bytes(b"\xff\n{bad\n[]\n{}\n")
    assert adapter.read(path) == []
    path.write_bytes(b"")
    assert adapter.read(path) == []


@pytest.mark.parametrize(
    "text",
    [
        "English message.",
        "运行完整测试并检查最终 diff。",
        "检查 CI 后创建 PR。",
        "Review 🚀 changes.",
    ],
)
def test_unicode(tmp_path, text):
    path = write_records(tmp_path / "session", [record("assistant", text)])
    assert CodexConversationAdapter().read(path) == [Message("assistant", text)]


def test_filter_tools_reasoning_images_logs_and_duplicates(tmp_path):
    records = [
        record("user", "Fix the login bug."),
        {"type": "event_msg", "payload": {"type": "user_message", "message": "Fix the login bug."}},
        {"type": "response_item", "payload": {"type": "function_call", "arguments": "bad"}},
        {"type": "response_item", "payload": {"type": "function_call_output", "output": "logs"}},
        record("assistant", "Hidden thoughts.", "analysis"),
        record("system", "Metadata."),
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_image", "image_url": "binary"}],
            },
        },
        record(
            "assistant",
            "Implemented the fix.\n```bash\nterminal output\n```\n"
            "diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ line\n+source\n"
            "2026-10-03T20:00:00 debug logs\nTargeted tests pass.",
        ),
    ]
    path = write_records(tmp_path / "session", records)
    messages = CodexConversationAdapter().read(path)
    assert messages == [
        Message("user", "Fix the login bug."),
        Message("assistant", "Implemented the fix.\nTargeted tests pass."),
    ]


def test_legacy_event_fallback(tmp_path):
    path = write_records(
        tmp_path / "session",
        [
            {"type": "event_msg", "payload": {"type": "user_message", "message": "Fix the bug."}},
            {"type": "event_msg", "payload": {"type": "agent_reasoning", "text": "hidden"}},
            {
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "Fixed the bug."},
            },
        ],
    )
    assert len(CodexConversationAdapter().read(path)) == 2


def test_strict_context_limits_latest_content(settings):
    messages = [Message("assistant", "a" * 10000 + f" latest {i}") for i in range(20)]
    selected = bounded_messages(messages, settings["context"])
    assert len(format_context(selected)) <= 8000
    assert all(len(m.text) <= 2500 for m in selected)
    assert selected[-1].text.endswith("latest 19")
    assert selected[0].text.endswith("latest 16")


def test_bounded_tail_drops_partial_record(tmp_path):
    path = tmp_path / "session"
    path.write_bytes(
        b"x" * (TAIL_BYTES + 10) + b"\n" + json.dumps(record("user", "Latest request.")).encode()
    )
    assert CodexConversationAdapter().read(path) == [Message("user", "Latest request.")]


def test_redact_private_key_before_cleaning_or_clipping(tmp_path, settings):
    text = (
        "Private credential:\n-----BEGIN PRIVATE KEY-----\n"
        "FAKEKEYDATA\n-----END PRIVATE KEY-----\nReview the fix."
    )
    path = write_records(tmp_path / "session", [record("user", text)])
    context = format_context(
        bounded_messages(CodexConversationAdapter().read(path), settings["context"])
    )
    assert "FAKEKEYDATA" not in context
    assert "[REDACTED]" in context


def test_metadata_and_invalid_content(tmp_path):
    records = [
        record("user", "<environment_context>metadata</environment_context>"),
        record("user", "# AGENTS.md instructions\nDo internal work"),
        {"type": "response_item", "payload": {"type": "message", "role": "user", "content": {}}},
        record("assistant", "Visible completion."),
    ]
    path = write_records(tmp_path / "session", records)
    assert CodexConversationAdapter().read(path) == [Message("assistant", "Visible completion.")]
