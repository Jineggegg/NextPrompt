import json
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from nextprompt.config import ConfigError, ConfigStore, data_directory, validate_config


def test_defaults_copy_and_notify_without_writing(tmp_path):
    store = ConfigStore(tmp_path / "absent")
    cfg = store.load()
    assert cfg["enabled"] and cfg["clipboard"]["auto_copy"] is True and cfg["notify"] is True
    assert not store.root.exists()


@pytest.mark.parametrize(
    "raw",
    [
        [],
        "bad",
        {"version": 2},
        {"enabled": "false"},
        {"clipboard": {"auto_copy": 1}},
        {"context": {"last_messages": 6}},
        {"context": {"max_total_chars": 8001}},
        {"context": {"max_chars_per_message": 2501}},
        {"suggestion": {"max_words": 21}},
        {"suggestion": {"max_chars": 241}},
        {"model": {"reasoning": "high"}},
        {"model": {"name": "$(bad)"}},
        {"model": {"name": "sk-test-example-not-real"}},
        {"model": {"timeout_seconds": 20}},
        {"unexpected": True},
        {"privacy": {"redact_secrets": "yes"}},
        {"clipboard": []},
        {"language": "klingon"},
        {"notify": "yes"},
        {"language": None},
    ],
)
def test_invalid_config(raw):
    with pytest.raises(ConfigError):
        validate_config(raw)


def test_atomic_concurrent_updates(configured):
    def change(i):
        configured.update(lambda cfg: cfg.update(enabled=bool(i % 2)))

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(change, range(18)))
    assert isinstance(json.loads(configured.path.read_text())["enabled"], bool)
    assert not list(configured.root.glob("*.tmp"))
    assert not (configured.root / ".config.lock").exists()


def test_once_and_error_cooldown(configured):
    with ThreadPoolExecutor(max_workers=6) as pool:
        flags = list(pool.map(lambda _: configured.notice_once(".setup-notice"), range(12)))
    assert sum(flags) == 1
    assert configured.error_notice("model")
    assert not configured.error_notice("model")


def test_official_data_directory(monkeypatch, tmp_path):
    monkeypatch.delenv("PLUGIN_DATA", raising=False)
    monkeypatch.delenv("NEXTPROMPT_MARKETPLACE", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    assert data_directory() == tmp_path / "plugins/data/nextprompt-nextprompt"
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "official-data"))
    assert data_directory() == (tmp_path / "official-data").resolve()


@pytest.mark.parametrize("content", ["{bad", "[]", '{"enabled": "false"}'])
def test_malformed_file(tmp_path, content):
    (tmp_path / "config.json").write_text(content)
    with pytest.raises(ConfigError):
        ConfigStore(tmp_path).load()


def test_lock_retries_windows_delete_pending(configured, monkeypatch):
    """Windows briefly denies access to a lock file another thread is deleting."""
    real_open = os.open
    calls = []

    def flaky_open(path, flags, mode=0o777):
        if str(path).endswith(".config.lock") and not calls:
            calls.append(path)
            raise PermissionError(13, "Permission denied")
        return real_open(path, flags, mode)

    monkeypatch.setattr("nextprompt.config.os.open", flaky_open)
    monkeypatch.setattr("nextprompt.config.LOCK_RETRY_ERRORS", (FileExistsError, PermissionError))
    assert configured.update(lambda cfg: cfg.update(enabled=False))["enabled"] is False
    assert calls


def test_permission_error_is_not_retried_off_windows(configured, monkeypatch):
    monkeypatch.setattr("nextprompt.config.LOCK_RETRY_ERRORS", (FileExistsError,))
    monkeypatch.setattr(
        "nextprompt.config.os.open", Mock(side_effect=PermissionError(13, "Permission denied"))
    )
    with pytest.raises(PermissionError):
        configured.update(lambda cfg: cfg.update(enabled=False))
