import io
import base64
import json
import queue
import threading

import pytest

from neuroflow.harness_sdk import request_harness_sdk


class FakeProcess:
    def __init__(self, identity="deepseek-harness-sdk-runtime", reason="completed"):
        self.frames = queue.Queue()
        self.identity = identity
        self.reason = reason
        self.closed = False
        self.stdout = self
        self.stdin = self
        self.prompt_blocks = []

    def __iter__(self):
        while True:
            row = self.frames.get()
            if row is None:
                return
            yield json.dumps(row) + "\n"

    def write(self, raw):
        request = json.loads(raw)
        if request["method"] == "initialize":
            self.frames.put({"id": 1, "result": {"serverInfo": {"name": self.identity}}})
        elif request["method"] == "session/prompt":
            self.prompt_blocks = request["params"]["contentBlocks"]
            sid = request["params"]["sessionId"]
            def emit(method, **params):
                self.frames.put({"method": method, "params": {"sessionId": sid, **params}})
            emit("session.status", status="running")
            emit("session.event", event={"type": "assistant/message", "data": {"message": {"content": [{"type": "text", "text": "Actual answer"}]}}})
            emit("session.event", event={"type": "turn/end", "data": {"reason": {"kind": self.reason}}})
            emit("session.status", status="idle")
        elif request["method"] == "shutdown":
            self.closed = True
            self.frames.put(None)

    def flush(self): pass
    def close(self): pass
    def poll(self): return 0 if self.closed else None
    def wait(self, timeout): return 0


@pytest.mark.parametrize("identity,reason,cancel,error", [
    ("deepseek-harness-sdk-runtime", "completed", False, None),
    ("unexpected", "completed", False, "identity"),
    ("deepseek-harness-sdk-runtime", "error", False, "did not complete"),
    ("deepseek-harness-sdk-runtime", "completed", True, "cancelled"),
])
def test_sdk_protocol_and_owned_process_cleanup(monkeypatch, identity, reason, cancel, error):
    process = FakeProcess(identity, reason)
    monkeypatch.setattr("neuroflow.harness_sdk.shutil.which", lambda _: "dsh")
    monkeypatch.setattr("neuroflow.harness_sdk.subprocess.Popen", lambda *a, **k: process)
    event = threading.Event()
    if cancel:
        event.set()
    if error:
        with pytest.raises(RuntimeError, match=error):
            request_harness_sdk(provider="test", model="test", prompt="query", cancel_event=event)
    else:
        assert request_harness_sdk(provider="test", model="test", prompt="query") == "Actual answer"
    assert process.closed


def test_sdk_chart_image_uses_official_inline_image_block(monkeypatch):
    process = FakeProcess()
    monkeypatch.setattr("neuroflow.harness_sdk.shutil.which", lambda _: "dsh")
    monkeypatch.setattr("neuroflow.harness_sdk.subprocess.Popen", lambda *a, **k: process)
    image = b"\x89PNG\r\n\x1a\n" + b"small-test-image"
    assert request_harness_sdk(provider="test", model="test", prompt="interpret", image_png=image) == "Actual answer"
    assert process.prompt_blocks[0] == {"type": "text", "text": "interpret"}
    assert process.prompt_blocks[1] == {
        "type": "image", "data": base64.b64encode(image).decode("ascii"), "mimeType": "image/png",
    }
    assert process.closed


def test_sdk_rejects_non_png_before_launch():
    with pytest.raises(ValueError, match="Only PNG"):
        request_harness_sdk(provider="test", model="test", prompt="query", image_png=b"not-png")


def test_sdk_reports_blocked_nvm_launcher_without_masking_error(monkeypatch):
    class FailedLauncher:
        def __init__(self):
            self.stdin = self
            self.stdout = iter([])
            self.stderr = iter(["NVM blocked package-manager execution\n", "Event code: NVM4306\n"])

        def write(self, _): pass
        def flush(self): pass
        def close(self): pass
        def poll(self): return 1

    monkeypatch.setattr("neuroflow.harness_sdk.shutil.which", lambda _: "dsh")
    monkeypatch.setattr("neuroflow.harness_sdk.subprocess.Popen", lambda *a, **k: FailedLauncher())
    with pytest.raises(RuntimeError, match="NVM4306"):
        request_harness_sdk(provider="test", model="test", prompt="query")
