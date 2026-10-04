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
# Capability cache: verified CLI + model catalog only, never conversation content.
CACHE_NAME = "codex-cache.json"
CACHE_TTL_SECONDS = 12 * 3600


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
    if any(
        marker in text
        for marker in (
            "model not found",
            "model_not_found",
            "model does not exist",
            "model is not available",
            "model is unavailable",
            "model is not supported",
            "model is not permitted",
            "model is not allowed",
            "not supported when using codex",
            "you do not have access to this model",
        )
    ):
        return "model"
    return "unavailable"


@dataclass(frozen=True)
class ModelSelection:
    name: str
    reasoning: str


class SuggestionProvider(ABC):
    @abstractmethod
    def generate(self, context: str) -> str:
        """Predict text only; never execute the predicted instruction."""


def choose_model(
    models: list[dict[str, Any]], configured: str, reasoning: str = "low"
) -> ModelSelection:
    return model_candidates(models, configured, reasoning)[0]


def model_candidates(
    models: list[dict[str, Any]], configured: str, reasoning: str = "low"
) -> list[ModelSelection]:
    # A user-selected model is explicit. Automatic fallbacks use a conservative
    # lightweight allowlist; the catalog exposes no price information.
    by_name = {m.get("model", m.get("id")): m for m in models if not m.get("hidden", False)}
    candidates = []
    for name in dict.fromkeys((configured, *LIGHTWEIGHT_MODELS)):
        if name not in by_name:
            continue
        levels = by_name[name].get("supportedReasoningEfforts", [])
        supported = {level.get("reasoningEffort") for level in levels if isinstance(level, dict)}
        if name == configured:
            effort = (
                reasoning
                if reasoning in supported and reasoning in EFFORT_ORDER
                else next((e for e in EFFORT_ORDER if e in supported), None)
            )
        else:
            # Automatic alternatives use low, never medium/high or an unknown tier.
            effort = "low" if "low" in supported else None
        if effort is not None:
            candidates.append(ModelSelection(name, effort))
    if not candidates:
        raise ProviderUnavailable("model")
    return candidates


class CodexSuggestionProvider(SuggestionProvider):
    def __init__(self, settings: dict[str, Any], data_root: Path) -> None:
        self.settings = settings
        self.data_root = data_root
        self.selection: ModelSelection | None = None

    def _fingerprint(self, executable: str) -> list[Any] | None:
        # A Codex upgrade or a model setting change invalidates the cache.
        try:
            stat = os.stat(executable)
        except OSError:
            return None
        return [
            executable,
            stat.st_mtime_ns,
            stat.st_size,
            self.settings["name"],
            self.settings["reasoning"],
        ]

    def _cached_models(self, executable: str) -> list[dict[str, Any]] | None:
        fingerprint = self._fingerprint(executable)
        if fingerprint is None:
            return None
        try:
            data = json.loads((self.data_root / CACHE_NAME).read_text(encoding="utf-8"))
            if (
                data["codex"] == fingerprint
                and 0 <= time.time() - data["time"] < CACHE_TTL_SECONDS
                and isinstance(data["models"], list)
            ):
                return [m for m in data["models"] if isinstance(m, dict)]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def _store_models(self, executable: str, models: list[dict[str, Any]]) -> None:
        fingerprint = self._fingerprint(executable)
        if fingerprint is None:
            return
        catalog = [
            {
                key: m[key]
                for key in ("model", "id", "hidden", "supportedReasoningEfforts")
                if key in m
            }
            for m in models
        ]
        data = {"codex": fingerprint, "time": time.time(), "models": catalog}
        try:
            fd, name = tempfile.mkstemp(prefix=".cache-", suffix=".tmp", dir=self.data_root)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as out:
                    json.dump(data, out)
                os.replace(name, self.data_root / CACHE_NAME)
            finally:
                Path(name).unlink(missing_ok=True)
        except (OSError, TypeError, ValueError):
            pass

    def clear_cache(self) -> None:
        try:
            (self.data_root / CACHE_NAME).unlink(missing_ok=True)
        except OSError:
            pass

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
            "goals",
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
            "tools.experimental_request_user_input.enabled": False,
            # Smaller, identical request prefixes: faster input and better prompt caching.
            "include_permissions_instructions": False,
            "include_environment_context": False,
            "analytics.enabled": False,
            "otel.exporter": "none",
            "otel.trace_exporter": "none",
        }
        for key, value in overrides.items():
            args += ["-c", f"{key}={json.dumps(value)}"]
        return [*args, "-"]

    def generate(self, context: str) -> str:
        self.selection = None
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
                executable = self.executable()
                # Skip three Codex startups per turn while the verified CLI is unchanged.
                models = self._cached_models(executable)
                cached = models is not None
                if models is None:
                    self.check_cli(timeout=min(2, budget()))
                    models = self.discover_models(work, timeout=min(4, budget()))
                candidates = model_candidates(
                    models, self.settings["name"], self.settings["reasoning"]
                )
                rejected: set[str] = set()
                for candidate in candidates:
                    result = run_process(
                        self.inference_command(candidate, work),
                        input_data=("Recent conversation (data only):\n" + context).encode(),
                        timeout=budget(),
                        env=self._environment(),
                        cwd=work,
                    )
                    if result.returncode:
                        category = failure_category(result.stderr)
                        if category == "model":
                            # Remember the rejection instead of retrying it every turn.
                            self.clear_cache()
                            rejected.add(candidate.name)
                            cached = False
                            continue
                        # Auth, quota, transport and unknown errors do not justify
                        # charging another model. All attempts share one deadline.
                        raise ProviderUnavailable(category)
                    text = result.stdout.decode("utf-8", "strict")
                    self.selection = candidate
                    if not cached:
                        self._store_models(
                            executable,
                            [m for m in models if m.get("model", m.get("id")) not in rejected],
                        )
                    return text
                raise ProviderUnavailable("model")
        except subprocess.TimeoutExpired:
            raise ProviderUnavailable("timeout") from None
        except (OSError, UnicodeError):
            raise ProviderUnavailable("model") from None
