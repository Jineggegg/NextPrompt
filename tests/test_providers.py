import subprocess
from pathlib import Path

import pytest

from nextprompt.providers import (
    CodexSuggestionProvider,
    ModelSelection,
    ProviderUnavailable,
    choose_model,
    failure_category,
)


def model(name, levels=("low", "medium", "high"), hidden=False):
    return {
        "model": name,
        "hidden": hidden,
        "supportedReasoningEfforts": [{"reasoningEffort": e} for e in levels],
    }


def test_lowest_actual_effort_and_lightweight_fallback():
    assert choose_model([model("gpt-5.6-luna")], "gpt-5.6-luna") == ModelSelection(
        "gpt-5.6-luna", "low"
    )
    assert choose_model([model("gpt-6-luna")], "missing").name == "gpt-6-luna"
    assert (
        choose_model([model("custom-small", ("minimal",))], "custom-small").reasoning == "minimal"
    )


@pytest.mark.parametrize(
    "models",
    [
        [],
        [model("gpt-6-astra")],
        [model("gpt-5.6-luna", hidden=True)],
        [model("gpt-5.6-luna", ("high",))],
    ],
)
def test_never_fallback_to_expensive_or_high_reasoning(models):
    with pytest.raises(ProviderUnavailable):
        choose_model(models, "missing")


def test_inference_safety_flags(monkeypatch, settings, tmp_path):
    monkeypatch.setattr("nextprompt.providers.shutil.which", lambda _: "codex")
    provider = CodexSuggestionProvider(settings["model"], tmp_path)
    args = provider.inference_command(ModelSelection("gpt-5.6-luna", "low"), tmp_path)
    assert all(flag in args for flag in ("--ignore-user-config", "--ignore-rules", "--ephemeral"))
    assert args[args.index("-s") + 1] == "read-only"
    assert "hooks" in args and "plugins" in args and "shell_tool" in args
    assert 'web_search="disabled"' in args
    assert provider._environment()["NEXTPROMPT_INTERNAL"] == "1"
    assert args[-1] == "-"


def test_timeout_and_no_persistent_context(monkeypatch, settings, tmp_path):
    provider = CodexSuggestionProvider(settings["model"], tmp_path)
    monkeypatch.setattr(provider, "check_cli", lambda **k: "ok")
    monkeypatch.setattr(provider, "discover_models", lambda *a, **k: [model("gpt-5.6-luna")])
    monkeypatch.setattr(provider, "executable", lambda: "codex")

    def timeout(*a, **k):
        assert k["timeout"] <= 15
        assert k["cwd"] != Path.cwd()
        raise subprocess.TimeoutExpired("codex", 15)

    monkeypatch.setattr("nextprompt.providers.run_process", timeout)
    with pytest.raises(ProviderUnavailable, match="timeout"):
        provider.generate("USER:\nonly bounded, redacted input\n")
    assert list(tmp_path.iterdir()) == []


def test_provider_rejects_oversized_context_before_side_effects(settings, tmp_path):
    provider = CodexSuggestionProvider(settings["model"], tmp_path / "absent")
    with pytest.raises(ProviderUnavailable):
        provider.generate("x" * 8001)
    assert not provider.data_root.exists()


@pytest.mark.parametrize(
    ("stderr", "category"),
    [
        (b"unexpected status 401 Unauthorized", "authentication"),
        (b"Could not parse your authentication token", "authentication"),
        (b"Invalid authentication token", "authentication"),
        (b"Please log in", "authentication"),
        (b"Your refresh token has already been used", "authentication"),
        (b"HTTP 429 Too Many Requests", "quota"),
        (b"You've hit your usage limit", "quota"),
        (b"insufficient_quota", "quota"),
        (b"Model not found", "model"),
        (b"Unrecognized failure: sk-test-example-not-real", "model"),
    ],
)
def test_failure_categories_never_return_raw_cli_errors(stderr, category):
    assert failure_category(stderr) == category


def test_inference_auth_failure_is_safe_and_cleans_up(monkeypatch, settings, tmp_path):
    provider = CodexSuggestionProvider(settings["model"], tmp_path)
    monkeypatch.setattr(provider, "check_cli", lambda **k: "ok")
    monkeypatch.setattr(provider, "discover_models", lambda *a, **k: [model("gpt-5.6-luna")])
    monkeypatch.setattr(provider, "executable", lambda: "codex")
    monkeypatch.setattr(
        "nextprompt.providers.run_process",
        lambda *a, **k: subprocess.CompletedProcess(
            a, 1, b"", b"401 Unauthorized: sk-test-example-not-real"
        ),
    )
    with pytest.raises(ProviderUnavailable, match="^authentication$"):
        provider.generate("USER:\nA safe synthetic message.\n")
    assert not list(tmp_path.iterdir())
