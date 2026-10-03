"""Bounded subprocess lifetime, including descendants."""

from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def kill_process(process: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            process.kill()


def run_process(
    args: Sequence[str],
    *,
    input_data: bytes = b"",
    timeout: float = 3,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    kwargs = (
        {"start_new_session": True}
        if os.name == "posix"
        else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    )
    process = subprocess.Popen(
        list(args),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE if capture_output else subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture_output else subprocess.DEVNULL,
        env=env,
        cwd=cwd,
        **kwargs,
    )
    try:
        stdout, stderr = process.communicate(input_data, timeout=timeout)
    except BaseException:
        kill_process(process)
        process.communicate()
        raise
    return subprocess.CompletedProcess(list(args), process.returncode, stdout or b"", stderr or b"")


def model_list_rpc(
    args: Sequence[str], *, timeout: float, env: Mapping[str, str], cwd: Path
) -> list[dict[str, Any]]:
    """Perform the official handshake before model/list, then close the server."""
    kwargs = (
        {"start_new_session": True}
        if os.name == "posix"
        else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    )
    process = subprocess.Popen(
        list(args),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd=cwd,
        **kwargs,
    )
    records: queue.Queue[bytes] = queue.Queue(maxsize=512)
    deadline = time.monotonic() + timeout

    def reader() -> None:
        assert process.stdout is not None
        while line := process.stdout.readline(1024 * 1024):
            try:
                records.put_nowait(line)
            except queue.Full:
                return
        try:
            records.put_nowait(b"")
        except queue.Full:
            pass

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    def send(request: dict[str, Any]) -> None:
        assert process.stdin is not None
        process.stdin.write((json.dumps(request) + "\n").encode())
        process.stdin.flush()

    def reply(identifier: int) -> dict[str, Any]:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(list(args), timeout)
            try:
                line = records.get(timeout=remaining)
            except queue.Empty:
                raise subprocess.TimeoutExpired(list(args), timeout) from None
            if not line:
                raise ValueError("model discovery unavailable")
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if isinstance(data, dict) and data.get("id") == identifier:
                if not isinstance(data.get("result"), dict):
                    raise ValueError("model discovery unavailable")
                return data["result"]

    try:
        send(
            {
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "nextprompt", "version": "0.1.0"}},
            }
        )
        reply(1)
        send({"method": "initialized", "params": {}})
        models: list[dict[str, Any]] = []
        cursor = None
        for identifier in range(2, 7):
            send(
                {
                    "id": identifier,
                    "method": "model/list",
                    "params": {"limit": 100, "includeHidden": False, "cursor": cursor},
                }
            )
            result = reply(identifier)
            data = result.get("data")
            if not isinstance(data, list):
                raise ValueError("model discovery unavailable")
            models.extend(m for m in data if isinstance(m, dict))
            cursor = result.get("nextCursor")
            if not cursor:
                return models
        return models
    finally:
        kill_process(process)
        process.wait(timeout=2)
        thread.join(timeout=1)
        if process.stdin:
            process.stdin.close()
        if process.stdout:
            process.stdout.close()
