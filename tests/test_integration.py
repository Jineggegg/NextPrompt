"""Real Codex processes, official plugin installation, local simulated inference.

Opt in with NEXTPROMPT_RUN_CLI_INTEGRATION=1. No real tokens or model service.
The test-only launcher adds an official model-provider configuration to every
Codex process, so isolated child exec calls also use the loopback service.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from nextprompt.config import ConfigStore
from nextprompt.providers import CodexSuggestionProvider

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "Run the full regression suite and review the final diff."
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("NEXTPROMPT_RUN_CLI_INTEGRATION") != "1"
        or not shutil.which("codex")
        or os.name != "posix",
        reason="requires opt-in, POSIX and an installed Codex CLI",
    ),
]


@pytest.fixture
def real_cli(tmp_path, monkeypatch):
    real_codex = shutil.which("codex")
    requests = []
    controls = {
        "fail_child": False,
        "suggestion": PROMPT,
        "reject_model": None,
        "root_reply": "Implemented the redirect fix. Targeted tests passed.",
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            # HTTP-only Responses provider; no websocket or external calls.
            self.send_error(404)

        def do_POST(self):
            data = self.rfile.read(int(self.headers["Content-Length"]))
            body = json.loads(data)
            requests.append(body)
            context = json.dumps(body.get("input", []), ensure_ascii=False)
            child = "Recent conversation (data only)" in context
            if child and controls["fail_child"]:
                self.send_error(401, "Synthetic authentication failure")
                return
            if child and body.get("model") == controls["reject_model"]:
                error = json.dumps(
                    {"error": {"code": "model_not_found", "message": "Model not found"}}
                ).encode()
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(error)))
                self.end_headers()
                self.wfile.write(error)
                return
            text = controls["suggestion"] if child else controls["root_reply"]
            response_id = f"response-{len(requests)}"
            events = [
                {"type": "response.created", "response": {"id": response_id}},
                {
                    "type": "response.output_item.done",
                    "item": {
                        "id": "message-test",
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": text}],
                    },
                },
                {
                    "type": "response.completed",
                    "response": {
                        "id": response_id,
                        "usage": {
                            "input_tokens": 1,
                            "output_tokens": 1,
                            "total_tokens": 2,
                            "input_tokens_details": None,
                            "output_tokens_details": None,
                        },
                    },
                },
            ]
            payload = "".join("data: " + json.dumps(e) + "\n\n" for e in events).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    home = tmp_path / "codex-home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    launch = bin_dir / "codex"
    provider = {
        "name": "NextPrompt loopback test",
        "base_url": f"http://127.0.0.1:{server.server_port}/v1",
        "wire_api": "responses",
        "supports_websockets": False,
        "requires_openai_auth": False,
    }
    # JSON string literals are valid TOML string values; build a TOML inline table.
    table = "{" + ",".join(f"{k}={json.dumps(v)}" for k, v in provider.items()) + "}"
    overrides = [
        "-c",
        'model_provider="nextprompt-test"',
        "-c",
        "model_providers.nextprompt-test=" + table,
        "-c",
        "analytics.enabled=false",
    ]
    launch.write_text(
        f"#!{sys.executable}\nimport os,sys\n"
        f"os.execv({real_codex!r}, [{real_codex!r}, *sys.argv[1:], *{overrides!r}])\n"
    )
    launch.chmod(0o755)
    monkeypatch.setenv(
        "PATH",
        os.pathsep.join((str(bin_dir), str(Path(sys.executable).parent), os.environ["PATH"])),
    )
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.delenv("PLUGIN_DATA", raising=False)
    monkeypatch.delenv("NEXTPROMPT_MARKETPLACE", raising=False)
    cwd = tmp_path / "work"
    cwd.mkdir()
    try:
        yield {"home": home, "requests": requests, "cwd": cwd, "controls": controls}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def tool_names(request):
    """Every tool the child model could call, including code-mode nested tools."""
    names = set()

    def walk(tools, prefix=""):
        for tool in tools:
            name = prefix + str(tool.get("name") or tool.get("type"))
            names.add(name)
            walk(tool.get("tools", []), name + ".")

    walk(request.get("tools", []))
    for item in request.get("input", []):
        if isinstance(item, dict) and item.get("type") == "additional_tools":
            walk(item.get("tools", []))
    return names


def command(args, cwd):
    return subprocess.run(
        ["codex", *args], capture_output=True, text=True, cwd=cwd, timeout=30, check=False
    )


def install(cwd):
    result = command(["plugin", "marketplace", "add", str(ROOT), "--json"], cwd)
    assert result.returncode == 0, result.stderr
    result = command(["plugin", "add", "nextprompt@nextprompt", "--json"], cwd)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_official_plugin_install_remove_and_data_path(real_cli):
    metadata = install(real_cli["cwd"])
    expected = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())["version"]
    assert metadata["version"] == expected
    assert (Path(metadata["installedPath"]) / "hooks/stop.py").exists()
    result = command(["plugin", "list", "--marketplace", "nextprompt", "--json"], real_cli["cwd"])
    assert json.loads(result.stdout)["installed"][0]["enabled"] is True
    result = command(["plugin", "remove", "nextprompt@nextprompt", "--json"], real_cli["cwd"])
    assert result.returncode == 0


def test_real_provider_one_short_output_no_transcript(real_cli):
    store = ConfigStore()
    provider = CodexSuggestionProvider(store.load()["model"], store.root)
    value = provider.generate(
        "USER:\nFix the login redirect.\nASSISTANT:\nImplemented the fix. Targeted tests passed.\n"
    )
    assert value.strip() == PROMPT
    assert len(value.split()) <= 20
    assert len(real_cli["requests"]) == 1
    assert not list(real_cli["home"].rglob("rollout-*.jsonl"))
    assert not list(store.root.glob("inference-*"))
    request = real_cli["requests"][0]
    assert request["model"] == "gpt-5.6-luna"
    assert request.get("reasoning", {}).get("effort") == "low"
    # Codex 0.159+ also sends tools inside an `additional_tools` input item.
    assert tool_names(request) <= {"functions", "functions.exec", "functions.wait"}
    text = json.dumps(request["input"], ensure_ascii=False)
    assert "<environment_context>" not in text and "<permissions instructions>" not in text
    assert len(json.dumps(request)) < 10000  # Slim request: no goals or sandbox prose.


def test_real_provider_falls_back_after_model_rejection(real_cli):
    real_cli["controls"]["reject_model"] = "gpt-5.6-luna"
    store = ConfigStore()
    provider = CodexSuggestionProvider(store.load()["model"], store.root)
    assert provider.generate("USER:\nReview the synthetic change.\n").strip() == PROMPT
    assert provider.selection.name == "gpt-6-luna"
    assert provider.selection.reasoning == "low"
    requested = [r["model"] for r in real_cli["requests"]]
    # Codex may retry a rejected HTTP request before returning the model error.
    # NextPrompt must select exactly one alternative, with no larger model.
    assert requested[-1] == "gpt-6-luna"
    assert requested[:-1] and set(requested[:-1]) == {"gpt-5.6-luna"}
    assert not list(store.root.glob("inference-*"))


@pytest.mark.parametrize("prompt", [PROMPT, "运行完整测试并检查最终 diff 🚀。"])
def test_real_stop_hook_one_child_no_recursive_turn(real_cli, tmp_path, monkeypatch, prompt):
    real_cli["controls"]["suggestion"] = prompt
    monkeypatch.setenv("PYTHONIOENCODING", "ascii")
    installed = Path(install(real_cli["cwd"])["installedPath"])
    # Capture only synthetic Hook stdout in a test receipt, then forward the exact
    # JSON to Codex. Production NextPrompt never persists suggestions/transcripts.
    receipt = tmp_path / "hook-output.json"
    observer = tmp_path / "observer.py"
    observer.write_text(
        "import os,sys,subprocess\nfrom pathlib import Path\n"
        "p=subprocess.run([sys.executable,os.path.join(os.environ['PLUGIN_ROOT'],"
        "'hooks','stop.py')],input=sys.stdin.buffer.read(),capture_output=True)\n"
        f"Path({str(receipt)!r}).write_bytes(p.stdout)\n"
        "sys.stdout.buffer.write(p.stdout)\n"
    )
    hooks_path = installed / "hooks/hooks.json"
    hooks = json.loads(hooks_path.read_text())
    hooks["hooks"]["Stop"][0]["hooks"][0]["command"] = (
        shlex.quote(sys.executable) + " " + shlex.quote(str(observer))
    )
    hooks_path.write_text(json.dumps(hooks))
    store = ConfigStore()
    assert not store.path.exists()  # Real first-run install needs no setup.
    result = command(
        [
            "exec",
            "--skip-git-repo-check",
            "--color",
            "never",
            "-s",
            "read-only",
            "--dangerously-bypass-hook-trust",
            "-m",
            "gpt-5.6-luna",
            "-c",
            'model_reasoning_effort="low"',
            "Respond only with: done",
        ],
        real_cli["cwd"],
    )
    assert result.returncode == 0, result.stderr
    assert "hook: Stop Completed" in result.stderr
    assert len(real_cli["requests"]) == 2  # One root task, one inference; no second root task.
    assert "Recent conversation (data only)" in json.dumps(real_cli["requests"][1])
    rollouts = list(real_cli["home"].rglob("rollout-*.jsonl"))
    # The only persistent transcript belongs to the test's root Codex, not NextPrompt.
    assert len(rollouts) == 1
    output = json.loads(receipt.read_bytes())["systemMessage"].split("\n")
    # Auto-copy is the default; headless hosts report a manual-copy fallback.
    assert output[0] == "Next → " + prompt
    assert output[1] in (
        "✓ Copied to clipboard",
        "Clipboard unavailable — copy the prompt above manually.",
    )
    assert store.root == real_cli["home"] / "plugins/data/nextprompt-nextprompt"


def test_real_stop_model_failure_root_still_succeeds(real_cli):
    install(real_cli["cwd"])
    store = ConfigStore()
    store.update(lambda cfg: cfg["clipboard"].update(auto_copy=False))
    real_cli["controls"]["fail_child"] = True
    # A synthetic model authentication failure does not resume or fail the root.
    result = command(
        [
            "exec",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--dangerously-bypass-hook-trust",
            "-m",
            "gpt-5.6-luna",
            "Respond only with: done",
        ],
        real_cli["cwd"],
    )
    assert result.returncode == 0, result.stderr
    assert "hook: Stop Completed" in result.stderr
    requests = real_cli["requests"]
    roots = [r for r in requests if "Recent conversation (data only)" not in json.dumps(r)]
    assert len(roots) == 1  # CLI transport retries do not create a second root task.
    assert len(requests) >= 2


def test_real_inline_line_copied_without_a_child_request(real_cli, tmp_path):
    # Default inline mode: hooks ask the root model for the line; Stop copies it as is.
    line = "Add a regression test for the logout redirect."
    real_cli["controls"]["root_reply"] = f"Implemented the redirect fix.\n\nNext prompt: {line}"
    installed = Path(install(real_cli["cwd"])["installedPath"])
    receipt = tmp_path / "hook-output.json"
    observer = tmp_path / "observer.py"
    observer.write_text(
        "import os,sys,subprocess\nfrom pathlib import Path\n"
        "p=subprocess.run([sys.executable,os.path.join(os.environ['PLUGIN_ROOT'],"
        "'hooks','stop.py')],input=sys.stdin.buffer.read(),capture_output=True)\n"
        f"Path({str(receipt)!r}).write_bytes(p.stdout)\n"
        "sys.stdout.buffer.write(p.stdout)\n"
    )
    hooks_path = installed / "hooks/hooks.json"
    hooks = json.loads(hooks_path.read_text())
    hooks["hooks"]["Stop"][0]["hooks"][0]["command"] = (
        shlex.quote(sys.executable) + " " + shlex.quote(str(observer))
    )
    hooks_path.write_text(json.dumps(hooks))
    result = command(
        [
            "exec",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--dangerously-bypass-hook-trust",
            "-m",
            "gpt-5.6-luna",
            "Fix the logout redirect.",
        ],
        real_cli["cwd"],
    )
    assert result.returncode == 0, result.stderr
    for event in ("SessionStart", "UserPromptSubmit", "Stop"):
        assert f"hook: {event} Completed" in result.stderr
    assert len(real_cli["requests"]) == 1  # The root turn only; no suggestion request.
    root = json.dumps(real_cli["requests"][0], ensure_ascii=False)
    assert "NextPrompt is installed." in root  # SessionStart instruction
    assert "NextPrompt: end this reply" in root  # UserPromptSubmit reminder
    output = json.loads(receipt.read_bytes())["systemMessage"]
    # The reply already shows the line; the Hook only reports the copy outcome.
    assert output in (
        "✓ Copied to clipboard",
        "Clipboard unavailable — copy the prompt above manually.",
    )
