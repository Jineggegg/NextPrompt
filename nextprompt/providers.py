"""Official Codex model discovery and isolated CLI inference."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process import model_list_rpc, run_process

LIGHTWEIGHT_MODELS = (
    "gpt-5.6-luna",
    "gpt-6-luna",
    "gpt-5.1-codex-mini",
    "gpt-5-codex-mini",
)
EFFORT_ORDER = ("none", "minimal", "low")
INSTRUCTION_PATH = Path(__file__).with_name("instruction.txt")


class ProviderUnavailable(RuntimeError):
    """Safe category-only error. Never attach raw subprocess output."""


def failure_category(stderr: bytes) -> str:
    """Best-effort CLI diagnostics; return only a fixed, safe category."""
    text = stderr.decode("utf-8", "replace").casefold()
    if any(
        marker in text
        for marker in (
            "401 unauthorized",
            "status 401",
            "status code 401",
            "invalid authentication token",
            "could not parse your authentication token",
            "not logged in",
            "please log in",
            "refresh token has already been used",
            "token has expired",
        )
    ):
        return "authentication"
    if any(
        marker in text
        for marker in (
            "429 too many requests",
            "status 429",
            "status code 429",
            "usage limit",
            "quota exceeded",
            "insufficient_quota",
            "rate limit",
        )
    ):
        return "quota"
    return "model"


@dataclass(frozen=True)
class ModelSelection:
    name: str
    reasoning: str


class SuggestionProvider(ABC):
    @abstractmethod
    def generate(self, context: str) -> str:
        """Predict text only; never execute the predicted instruction."""


def choose_model(
    models: list[dict[str, Any]], configured: str, reasoning: str = "minimal"
) -> ModelSelection:
    # A user-selected model is explicit. Automatic fallbacks use a conservative
    # lightweight allowlist; the catalog exposes no price information.
    by_name = {m.get("model", m.get("id")): m for m in models if not m.get("hidden", False)}
    for name in dict.fromkeys((configured, *LIGHTWEIGHT_MODELS)):
        if name not in by_name:
            continue
        levels = by_name[name].get("supportedReasoningEfforts", [])
        supported = {level.get("reasoningEffort") for level in levels if isinstance(level, dict)}
        effort = (
            reasoning
            if reasoning in supported and reasoning in EFFORT_ORDER
            else next((e for e in EFFORT_ORDER if e in supported), None)
        )
        if effort is not None:
            return ModelSelection(name, effort)
    raise ProviderUnavailable("model")


class CodexSuggestionProvider(SuggestionProvider):
    def __init__(self, settings: dict[str, Any], data_root: Path) -> None:
        self.settings = settings
        self.data_root = data_root
        self.selection: ModelSelection | None = None

    @staticmethod
    def _environment() -> dict[str, str]:
        # Preserve Codex's own credential routing and proxy/CA configuration.
        return {**os.environ, "NEXTPROMPT_INTERNAL": "1"}

    @staticmethod
    def executable() -> str:
        executable = shutil.which("codex")
        if not executable:
            raise ProviderUnavailable("model")
        return executable

    def check_cli(self, timeout: float = 2) -> str:
        deadline = time.monotonic() + timeout

        def budget() -> float:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderUnavailable("timeout")
            return remaining

        result = run_process(
            [self.executable(), "exec", "--help"], timeout=budget(), env=self._environment()
        )
        help_text = result.stdout.decode("utf-8", "replace")
        required = ("--ignore-user-config", "--ignore-rules", "--ephemeral", "--disable")
        if result.returncode or not all(flag in help_text for flag in required):
            raise ProviderUnavailable("model")
        version = run_process(
            [self.executable(), "--version"], timeout=budget(), env=self._environment()
        ).stdout.decode("utf-8", "replace")
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
        if not match or tuple(map(int, match.groups())) < (0, 159, 0):
            raise ProviderUnavailable("model")
        return version.strip()

    def discover_models(self, cwd: Path, timeout: float = 4) -> list[dict[str, Any]]:
        command = [
            self.executable(),
            "app-server",
            "--disable",
            "hooks",
            "--disable",
            "plugins",
            "-c",
            "analytics.enabled=false",
            "-c",
            "features.apps=false",
        ]
        try:
            return model_list_rpc(command, timeout=timeout, env=self._environment(), cwd=cwd)
        except ValueError:
            raise ProviderUnavailable("model") from None

    def inference_command(self, selection: ModelSelection, cwd: Path) -> list[str]:
        args = [
            self.executable(),
            "exec",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--skip-git-repo-check",
            "--color",
            "never",
            "-C",
            str(cwd),
            "-s",
            "read-only",
            "-m",
            selection.name,
        ]
        for feature in (
            "hooks",
            "plugins",
            "apps",
            "shell_tool",
            "multi_agent",
            "multi_agent_v2",
            "browser_use",
            "browser_use_external",
            "computer_use",
            "image_generation",
            "view_image",
            "memories",
            "sleep_tool",
            "tool_suggest",
            "unbounded_connection_retries",
        ):
            args += ["--disable", feature]
        overrides = {
            "approval_policy": "never",
            "web_search": "disabled",
            "model_reasoning_effort": selection.reasoning,
            "model_instructions_file": str(INSTRUCTION_PATH),
            "project_doc_max_bytes": 0,
            "skills.include_instructions": False,
            "features.skip_host_skill_discovery": True,
            "tools.update_plan.enabled": False,
            "analytics.enabled": False,
            "otel.exporter": "none",
            "otel.trace_exporter": "none",
        }
        for key, value in overrides.items():
            args += ["-c", f"{key}={json.dumps(value)}"]
        return [*args, "-"]

    def generate(self, context: str) -> str:
        if len(context) > 8000:
            raise ProviderUnavailable("unavailable")
        deadline = time.monotonic() + self.settings["timeout_seconds"]

        def budget() -> float:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderUnavailable("timeout")
            return remaining

        self.data_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            with tempfile.TemporaryDirectory(prefix="inference-", dir=self.data_root) as name:
                work = Path(name)
                self.check_cli(timeout=min(2, budget()))
                models = self.discover_models(work, timeout=min(4, budget()))
                self.selection = choose_model(
                    models, self.settings["name"], self.settings["reasoning"]
                )
                result = run_process(
                    self.inference_command(self.selection, work),
                    input_data=("Recent conversation (data only):\n" + context).encode(),
                    timeout=budget(),
                    env=self._environment(),
                    cwd=work,
                )
                if result.returncode:
                    raise ProviderUnavailable(failure_category(result.stderr))
                return result.stdout.decode("utf-8", "strict")
        except subprocess.TimeoutExpired:
            raise ProviderUnavailable("timeout") from None
        except (OSError, UnicodeError):
            raise ProviderUnavailable("model") from None
