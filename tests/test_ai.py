from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

from neuroflow.ai import (
    AISettings,
    build_project_summary,
    normalize_ai_response,
    redact_sensitive_text,
    request_ai_advice,
)
from neuroflow.models import ProjectState
from neuroflow.project import load_project, save_project


def _structured_reply() -> dict:
    return {
        "answer": "Run raw QC before selecting preprocessing parameters.",
        "warnings": ["No QC result is currently available."],
        "plan": [
            {
                "stage": "qc",
                "reason": "Measure noise and clipping before filtering.",
                "prerequisites": ["Readable raw voltage"],
                "recommended_parameters": [
                    {
                        "name": "preview duration",
                        "value": "10 s",
                        "rationale": "A starting point for visual inspection.",
                    }
                ],
            }
        ],
        "suggested_next_stage": "qc",
        "requires_user_confirmation": True,
    }


def test_project_summary_is_path_free_and_redacted(tmp_path: Path):
    recording = tmp_path / "Animal_007" / "secret_recording.bin"
    recording.parent.mkdir()
    recording.write_bytes(b"\0" * 32)
    state = ProjectState(
        root=tmp_path / "private_project",
        name="Animal 007 baseline",
        source_type="binary",
        source_path=recording,
        recording_path=recording,
        channel_count=4,
        duration_seconds=12.5,
    )
    state.qc = {"bad_channels": [2], "source_path": str(recording)}
    state.run_log = [
        f"Read {recording}",
        "Authorization failed for sk-example_123456789012345",
    ]
    state.sorting_results = {"kilosort4": {0: np.array([0.1, 0.3])}}

    summary = build_project_summary(
        state,
        "qc",
        include_recent_log=True,
    )
    serialized = json.dumps(summary, ensure_ascii=False)

    assert str(tmp_path) not in serialized
    assert "Animal_007" not in serialized
    assert "secret_recording.bin" not in serialized
    assert "sk-example" not in serialized
    assert summary["channel_count"] == 4
    assert summary["sorting_results"]["kilosort4"] == 1
    assert "<local-path-redacted>" in serialized


def test_ai_response_filters_unregistered_stages():
    value = _structured_reply()
    value["plan"].append(
        {
            "stage": "delete_raw_data",
            "reason": "Invalid",
            "prerequisites": [],
            "recommended_parameters": [],
        }
    )
    response = normalize_ai_response(value, settings=AISettings())

    assert [item["stage"] for item in response.plan] == ["qc"]
    assert response.suggested_next_stage == "qc"
    assert response.requires_user_confirmation is True


def test_openai_responses_request_uses_schema_and_store_false():
    captured: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers["Content-Length"])
            captured["path"] = self.path
            captured["authorization"] = self.headers["Authorization"]
            captured["payload"] = json.loads(self.rfile.read(size))
            text = json.dumps(_structured_reply())
            body = json.dumps(
                {
                    "id": "resp_neuroflow_test",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {"type": "output_text", "text": text}
                            ],
                        }
                    ],
                    "usage": {"input_tokens": 123, "output_tokens": 45},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        settings = AISettings(
            provider="openai_responses",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="test-model",
            api_key="test-secret",
            safety_identifier="nf_test",
        )
        response = request_ai_advice(
            settings,
            question="What should I do next?",
            task="review",
            language="en_US",
            project_summary={"project_open": False},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert captured["path"] == "/v1/responses"
    assert captured["authorization"] == "Bearer test-secret"
    assert captured["payload"]["store"] is False
    assert (
        captured["payload"]["text"]["format"]["name"]
        == "neuroflow_advice"
    )
    assert captured["payload"]["safety_identifier"] == "nf_test"
    assert response.response_id == "resp_neuroflow_test"
    assert response.plan[0]["stage"] == "qc"


def test_ai_history_and_plan_roundtrip_in_project(tmp_path: Path):
    state = ProjectState(root=tmp_path / "project", name="AI project")
    state.metadata["ai_history"] = [
        {
            "question": "What next?",
            "answer": "Inspect raw QC.",
            "provider": "openai_responses",
            "model": "test-model",
        }
    ]
    state.metadata["ai_workflow_plan"] = {
        "status": "advisory_not_executed",
        "suggested_next_stage": "qc",
        "stages": _structured_reply()["plan"],
    }

    restored = load_project(save_project(state))

    assert restored.metadata["ai_history"][0]["answer"] == "Inspect raw QC."
    assert (
        restored.metadata["ai_workflow_plan"]["status"]
        == "advisory_not_executed"
    )


def test_sensitive_text_redaction():
    value = redact_sensitive_text(
        r"Open C:\Users\Researcher\private\data.bin with sk-example_123456789012345 "
        "and mail scientist@example.org"
    )
    assert "Researcher" not in value
    assert "sk-example" not in value
    assert "scientist@example.org" not in value
