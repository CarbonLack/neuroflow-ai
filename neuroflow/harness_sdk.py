"""Client for the installed official Harness SDK stdio protocol.

The Harness owns authentication and provider calls. No key is read by this module.
Protocol source: @deepseek-ai/dsh-sdk-protocol and dsh-sdk-jsonrpc-server.
"""
from __future__ import annotations

import json
import queue
import shutil
import subprocess
import threading
import time
import uuid
import tempfile
import yaml
from pathlib import Path
from typing import Callable


def request_harness_sdk(*, provider: str, model: str, prompt: str,
                        timeout: int = 120, cancel_event=None,
                        on_text: Callable[[str], None] | None = None,
                        bridge=None) -> str:
    executable = shutil.which("dsh")
    if not executable:
        raise RuntimeError("DeepSeek Harness is not installed or dsh is not on PATH.")
    patch = Path(__file__).with_name("harness_sdk.patch.yml")
    temporary = tempfile.TemporaryDirectory(prefix="neuroephys-harness-")
    if bridge is not None:
        rows = yaml.safe_load(patch.read_text(encoding="utf-8"))
        rows.append({"insert": [{"id": "mcp-neuroephys", "name": "@deepseek-ai/dsh-mcp-client",
            "config": {"serverName": "neuroephys", "transport": "streamable-http",
                       "url": bridge.url, "headers": {"Authorization": "Bearer " + bridge.token},
                       "failOnStartupError": True}}]})
        patch = Path(temporary.name) / "bridge.patch.yml"
        patch.write_text(yaml.safe_dump(rows, allow_unicode=True), encoding="utf-8")
    try:
        process = subprocess.Popen(
            [executable, "--profile", "sdk", "--patch", str(patch)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        temporary.cleanup()
        raise
    frames: queue.Queue = queue.Queue()

    def read_frames():
        for line in process.stdout:
            try:
                frames.put(json.loads(line))
            except json.JSONDecodeError:
                continue
        frames.put(None)

    threading.Thread(target=read_frames, daemon=True).start()
    deadline = time.monotonic() + max(30, timeout)
    session = "neuroephys-" + uuid.uuid4().hex

    def send(method, params, request_id):
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id,
            "method": method, "params": params}, ensure_ascii=False) + "\n")
        process.stdin.flush()

    def receive():
        while time.monotonic() < deadline:
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("AI request cancelled.")
            try:
                frame = frames.get(timeout=0.2)
            except queue.Empty:
                continue
            if frame is None:
                raise RuntimeError("Harness SDK process closed before completing the answer.")
            if frame.get("error"):
                raise RuntimeError("Harness SDK rejected the request: " +
                    str(frame["error"].get("message", "unknown error")))
            return frame
        raise RuntimeError("Harness SDK request timed out.")

    try:
        send("initialize", {"cwd": temporary.name, "provider": provider,
             "model": model, "maxTokens": 8192}, 1)
        while True:
            frame = receive()
            if frame.get("id") == 1:
                if frame.get("result", {}).get("serverInfo", {}).get("name") != "deepseek-harness-sdk-runtime":
                    raise RuntimeError("Unexpected Harness SDK server identity.")
                break
        send("session/prompt", {"sessionId": session,
            "contentBlocks": [{"type": "text", "text": prompt}]}, 2)
        answer = ""
        running = False
        finish_reason = None
        while True:
            frame = receive()
            params = frame.get("params", {})
            if params.get("sessionId") != session:
                continue
            if frame.get("method") == "session.event":
                event = params.get("event", {})
                if event.get("type") == "turn/end":
                    finish_reason = event.get("data", {}).get("reason", {}).get("kind")
                if event.get("type") == "assistant/message":
                    data = event.get("data", {})
                    blocks = data.get("message", {}).get("content", [])
                    text = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")
                    if text:
                        answer = text
                        if on_text:
                            on_text(text)
            if frame.get("method") == "session.status":
                if params.get("status") == "running":
                    running = True
                elif running and params.get("status") == "idle":
                    if finish_reason in {"error", "cancelled", "max-tokens"}:
                        raise RuntimeError("Harness turn did not complete: " + finish_reason)
                    if not answer.strip():
                        raise RuntimeError("Harness completed without an assistant answer.")
                    return answer
    finally:
        if process.poll() is None:
            try:
                send("shutdown", {}, 3)
                process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
                process.wait(timeout=5)
        for pipe in (process.stdin, process.stdout):
            if pipe:
                pipe.close()
        temporary.cleanup()
