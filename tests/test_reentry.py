from unittest.mock import Mock

import pytest

from nextprompt.hook import handle_stop

PAYLOAD = {"hook_event_name": "Stop", "transcript_path": "unused"}


def test_internal_guard_before_any_read(monkeypatch, provider, clipboard):
    monkeypatch.setenv("NEXTPROMPT_INTERNAL", "1")
    store = Mock()
    conversation = Mock()
    assert (
        handle_stop(
            PAYLOAD, store=store, conversation=conversation, provider=provider, clipboard=clipboard
        )
        is None
    )
    store.load.assert_not_called()
    conversation.read.assert_not_called()
    provider.generate.assert_not_called()
    clipboard.available.assert_not_called()
    clipboard.copy.assert_not_called()


@pytest.mark.parametrize("mode", ["disabled", "manual", "code_change_only"])
def test_disabled_zero_side_effects(mode, configured, provider, clipboard):
    configured.update(
        lambda cfg: cfg.update(
            enabled=mode != "disabled", trigger_mode="every_turn" if mode == "disabled" else mode
        )
    )
    before = {p.name: p.read_bytes() for p in configured.root.iterdir() if p.is_file()}
    conversation = Mock()
    assert (
        handle_stop(
            PAYLOAD,
            store=configured,
            conversation=conversation,
            provider=provider,
            clipboard=clipboard,
        )
        is None
    )
    after = {p.name: p.read_bytes() for p in configured.root.iterdir() if p.is_file()}
    assert before == after
    conversation.read.assert_not_called()
    provider.generate.assert_not_called()
    clipboard.available.assert_not_called()
