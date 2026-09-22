"""Client for the installed official Harness SDK stdio protocol.

The Harness owns authentication and provider calls. No key is read by this module.
Protocol source: @deepseek-ai/dsh-sdk-protocol and dsh-sdk-jsonrpc-server.
"""
from __future__ import annotations

import json
import base64
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
                        bridge=None, image_png: bytes | None = None) -> str:
    if image_png is not None:
        if not image_png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Only PNG chart attachments are supported.")
        if len(image_png) > 6_000_000:
            raise ValueError("The chart image exceeds the 6 MB attachment limit.")
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
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        temporary.cleanup()
        raise
    frames: queue.Queue = queue.Queue()
    launcher_output: list[str] = []
    diagnostics_done = threading.Event()

    def read_diagnostics():
        stderr = getattr(process, "stderr", None)
        if stderr is not None:
            for line in stderr:
                if len(launcher_output) < 12:
                    launcher_output.append(line.strip()[:300])
        diagnostics_done.set()

    threading.Thread(target=read_diagnostics, daemon=True).start()

    def read_frames():
        for line in process.stdout:
            try:
                frames.put(json.loads(line))
            except json.JSONDecodeError:
                # Some launchers report an actionable local error before any JSON.
                if len(launcher_output) < 12:
                    launcher_output.append(line.strip()[:300])
                continue
        frames.put(None)

    threading.Thread(target=read_frames, daemon=True).start()
    started = time.monotonic()
    idle_seconds = max(60, int(timeout))
    overall_deadline = started + max(900, idle_seconds * 4)
    last_frame_at = started
    phase = "initialization"
    session = "neuroephys-" + uuid.uuid4().hex

    def send(method, params, request_id):
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id,
            "method": method, "params": params}, ensure_ascii=False) + "\n")
        process.stdin.flush()

    def receive():
        nonlocal last_frame_at
        while True:
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("AI request cancelled.")
            now = time.monotonic()
            if now >= overall_deadline or now - last_frame_at >= idle_seconds:
                elapsed = round(now - started)
                raise RuntimeError(
                    f"Harness {phase} timed out after {elapsed} s; no protocol activity "
                    f"for {round(now - last_frame_at)} s (idle limit {idle_seconds} s). "
                    "The request may have reached the model; retry only after checking "
                    "the conversation and network to avoid duplicate work."
                )
            try:
                frame = frames.get(timeout=0.2)
            except queue.Empty:
                continue
            if frame is None:
                diagnostics_done.wait(timeout=0.5)
                if any("NVM blocked package-manager execution" in row for row in launcher_output):
                    raise RuntimeError(
                        "The local NVM launcher blocked dsh (NVM4306). Run 'nvm reshim' "
                        "or ask the computer administrator to repair the trusted launcher, "
                        "then verify 'dsh --version'. No model request was sent."
                    )
                raise RuntimeError(
                    "Harness SDK process closed before completing the answer. "
                    "Check 'dsh --version' in a terminal to diagnose the local launcher."
                )
            if frame.get("error"):
                raise RuntimeError("Harness SDK rejected the request: " +
                    str(frame["error"].get("message", "unknown error")))
            last_frame_at = time.monotonic()
            return frame

    try:
        send("initialize", {"cwd": temporary.name, "provider": provider,
             "model": model, "maxTokens": 8192}, 1)
        while True:
            frame = receive()
            if frame.get("id") == 1:
                if frame.get("result", {}).get("serverInfo", {}).get("name") != "deepseek-harness-sdk-runtime":
                    raise RuntimeError("Unexpected Harness SDK server identity.")
                break
        blocks = [{"type": "text", "text": prompt}]
        phase = "answer"
        if image_png is not None:
            blocks.append({"type": "image", "data": base64.b64encode(image_png).decode("ascii"),
                           "mimeType": "image/png"})
        send("session/prompt", {"sessionId": session, "contentBlocks": blocks}, 2)
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
        for pipe in (process.stdin, process.stdout, getattr(process, "stderr", None)):
            if pipe and hasattr(pipe, "close"):
                try:
                    pipe.close()
                except OSError:
                    pass  # A failed Windows launcher may already have invalidated its pipe.
        temporary.cleanup()
