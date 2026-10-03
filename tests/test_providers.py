import subprocess
from pathlib import Path

import pytest

from nextprompt.providers import (
    CodexSuggestionProvider,
    ModelSelection,
    ProviderUnavailable,
    choose_model,
    failure_category,
    model_candidates,
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
        (b"Unrecognized failure: sk-test-example-not-real", "unavailable"),
        (b"Connection reset by peer", "unavailable"),
        (b"503 Service Unavailable", "unavailable"),
        (b"The model is not supported when using Codex with a ChatGPT account", "model"),
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


def test_candidates_deduplicate_and_require_low_for_automatic_alternatives():
    assert model_candidates(
        [model("gpt-5.6-luna"), model("gpt-6-luna"), model("gpt-6-astra")],
        "gpt-5.6-luna",
    ) == [ModelSelection("gpt-5.6-luna", "low"), ModelSelection("gpt-6-luna", "low")]
    with pytest.raises(ProviderUnavailable, match="^model$"):
        model_candidates([model("gpt-6-luna", ("minimal", "high"))], "missing")


@pytest.fixture
def fallback_provider(monkeypatch, settings, tmp_path):
    provider = CodexSuggestionProvider(settings["model"], tmp_path)
    monkeypatch.setattr(provider, "check_cli", lambda **k: "ok")
    monkeypatch.setattr(
        provider,
        "discover_models",
        lambda *a, **k: [model("gpt-5.6-luna"), model("gpt-6-luna"), model("gpt-6-astra")],
    )
    monkeypatch.setattr(provider, "executable", lambda: "codex")
    return provider


def test_runtime_model_rejection_falls_back_low(monkeypatch, fallback_provider, tmp_path):
    calls = []

    def infer(command, **kwargs):
        calls.append((command, kwargs))
        if len(calls) == 1:
            return subprocess.CompletedProcess(command, 1, b"", b"Model not found")
        return subprocess.CompletedProcess(command, 0, b"Review the final diff for regressions.")

    monkeypatch.setattr("nextprompt.providers.run_process", infer)
    assert fallback_provider.generate("USER:\nReview the change.\n") == (
        "Review the final diff for regressions."
    )
    assert [c[c.index("-m") + 1] for c, _ in calls] == ["gpt-5.6-luna", "gpt-6-luna"]
    assert all('model_reasoning_effort="low"' in c for c, _ in calls)
    assert calls[0][1]["input_data"] == calls[1][1]["input_data"]
    assert 0 < calls[1][1]["timeout"] <= calls[0][1]["timeout"] <= 15
    assert fallback_provider.selection == ModelSelection("gpt-6-luna", "low")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    ("stderr", "category"),
    [
        (b"401 Unauthorized", "authentication"),
        (b"429 Too Many Requests", "quota"),
        (b"Connection reset", "unavailable"),
        (b"Unknown error", "unavailable"),
    ],
)
def test_non_model_errors_never_try_another_model(
    monkeypatch, fallback_provider, tmp_path, stderr, category
):
    calls = []

    def infer(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, b"", stderr)

    monkeypatch.setattr("nextprompt.providers.run_process", infer)
    with pytest.raises(ProviderUnavailable, match=f"^{category}$"):
        fallback_provider.generate("USER:\nSafe synthetic context.\n")
    assert len(calls) == 1
    assert fallback_provider.selection is None
    assert not list(tmp_path.iterdir())


def test_all_model_rejections_exhaust_bounded_candidates(monkeypatch, fallback_provider):
    calls = []

    def infer(command, **kwargs):
        calls.append(command[command.index("-m") + 1])
        return subprocess.CompletedProcess(command, 1, b"", b"Model not found")

    monkeypatch.setattr("nextprompt.providers.run_process", infer)
    with pytest.raises(ProviderUnavailable, match="^model$"):
        fallback_provider.generate("USER:\nSafe synthetic context.\n")
    assert calls == ["gpt-5.6-luna", "gpt-6-luna"]


def test_fallback_cannot_reset_deadline(monkeypatch, fallback_provider, tmp_path):
    clock = [100.0]
    monkeypatch.setattr("nextprompt.providers.time.monotonic", lambda: clock[0])
    calls = []

    def infer(command, **kwargs):
        calls.append(command)
        clock[0] += 15
        return subprocess.CompletedProcess(command, 1, b"", b"Model not found")

    monkeypatch.setattr("nextprompt.providers.run_process", infer)
    with pytest.raises(ProviderUnavailable, match="^timeout$"):
        fallback_provider.generate("USER:\nSafe synthetic context.\n")
    assert len(calls) == 1
    assert not list(tmp_path.iterdir())
