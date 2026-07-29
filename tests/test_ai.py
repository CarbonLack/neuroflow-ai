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
from neuroflow.ai_tools import AIMode, validate_tool_call
from neuroflow.models import ProjectState
from neuroflow.project import load_project, save_project
from neuroflow.unit_curation import save_unit_curation


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
        "Authorization failed for sess-example_123456789012345",
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
    assert "sess-example" not in serialized
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
        r"Open C:\Users\Researcher\private\data.bin with sess-example_123456789012345 "
        "and mail scientist@example.org"
    )
    assert "Researcher" not in value
    assert "sess-example" not in value
    assert "scientist@example.org" not in value


def test_ai_modes_block_tools_until_collaborative(tmp_path: Path):
    recording = tmp_path / "recording.bin"
    recording.write_bytes(b"\0" * 1024)
    state = ProjectState(
        root=tmp_path / "project",
        recording_path=recording,
        channel_count=4,
        duration_seconds=30,
    )
    state.sorted_spikes = {0: np.array([0.1, 0.3])}
    state.events = [{"time_seconds": 1.0, "event_code": 21}]

    blocked = validate_tool_call(
        "run_raw_qc",
        {"preview_seconds": 10},
        state,
        AIMode.ASSISTANT,
    )
    allowed = validate_tool_call(
        "run_raw_qc",
        {"preview_seconds": 10},
        state,
        AIMode.COLLABORATIVE,
    )
    unknown = validate_tool_call(
        "delete_raw_data",
        {},
        state,
        AIMode.COLLABORATIVE,
    )

    assert blocked.valid is False
    assert allowed.valid is True
    assert unknown.valid is False


def test_ai_context_reports_online_highpass_and_never_exposes_path(tmp_path: Path):
    recording = tmp_path / "private" / "ap_recording.bin"
    recording.parent.mkdir()
    recording.write_bytes(b"\0" * 32)
    state = ProjectState(
        root=tmp_path / "project",
        source_path=recording,
        recording_path=recording,
        channel_count=32,
        duration_seconds=1800,
    )
    state.metadata["acquisition"] = {
        "online_highpass_hz": 250,
        "lfp_available": False,
    }

    summary = build_project_summary(state, "analysis")
    serialized = json.dumps(summary)

    assert summary["acquisition_settings"]["online_highpass_hz"] == 250
    assert "ap_recording.bin" not in serialized
    assert str(tmp_path) not in serialized


def test_ai_context_normalizes_real_acquisition_metadata_and_provenance(
    tmp_path: Path,
):
    state = ProjectState(root=tmp_path / "project", channel_count=32)
    state.metadata["acquisition_preprocessing"] = {
        "settings_file": str(tmp_path / "private" / "settings.xml"),
        "online_filters": [{"low_cut_hz": 250, "high_cut_hz": 8000}],
        "lfp_available": False,
    }
    state.metadata["external_observations"] = [
        {
            "type": "reported_unit_count",
            "value": 8,
            "verification_status": "unverified",
        }
    ]
    state.metadata["structured_run_log"] = [
        {
            "run_id": "1234567890abcdef",
            "stage": "sorting",
            "tool": "Kilosort4",
            "parameters": {"Th_universal": 9},
            "input_files": [str(tmp_path / "private" / "recording.bin")],
            "elapsed_seconds": 10.5,
            "status": "completed",
            "warnings": [],
            "artifacts": [{"id": "artifact-1"}],
        }
    ]

    summary = build_project_summary(state, "unit_qc")
    serialized = json.dumps(summary)

    assert summary["acquisition_settings"]["online_highpass_hz"] == 250
    assert summary["external_observations"][0]["value"] == 8
    assert summary["recent_stage_runs"][0]["artifact_ids"] == ["artifact-1"]
    assert "settings.xml" not in serialized
    assert "recording.bin" not in serialized


def test_lfp_warning_uses_real_acquisition_preprocessing_schema(tmp_path: Path):
    recording = tmp_path / "recording.bin"
    recording.write_bytes(b"\0" * 64)
    state = ProjectState(
        root=tmp_path / "project",
        recording_path=recording,
        channel_count=4,
    )
    state.metadata["acquisition_preprocessing"] = {
        "online_filters": [{"low_cut_hz": 250, "high_cut_hz": 8000}],
        "lfp_available": False,
    }

    validation = validate_tool_call(
        "run_raw_qc",
        {"preview_seconds": 10},
        state,
        AIMode.COLLABORATIVE,
    )

    assert validation.valid is True
    assert any("250 Hz" in warning for warning in validation.warnings)


def test_sorter_duration_must_match_the_imported_project_segment(tmp_path: Path):
    recording = tmp_path / "recording.bin"
    recording.write_bytes(b"\0" * 64)
    state = ProjectState(
        root=tmp_path / "project",
        recording_path=recording,
        channel_count=4,
        duration_seconds=1800,
    )

    mismatched = validate_tool_call(
        "run_sorter",
        {
            "sorter": "kilosort4",
            "duration_seconds": 600,
            "parameters": {},
        },
        state,
        AIMode.COLLABORATIVE,
    )
    matched = validate_tool_call(
        "run_sorter",
        {
            "sorter": "kilosort4",
            "duration_seconds": 1800,
            "parameters": {},
        },
        state,
        AIMode.COLLABORATIVE,
    )

    assert mismatched.valid is False
    assert any("project segment" in error for error in mismatched.errors)
    assert matched.valid is True


def test_manual_unit_curation_is_project_scoped_and_roundtrips(tmp_path: Path):
    state = ProjectState(root=tmp_path / "project", duration_seconds=10)
    state.active_sorter_key = "kilosort4"
    state.sorted_spikes = {7: np.array([0.1, 0.2, 0.4])}
    state.sorting_results = {"kilosort4": state.sorted_spikes}
    state.unit_metrics = [
        {
            "unit_id": 7,
            "spike_count": 3,
            "firing_rate_hz": 0.3,
            "isi_violation_rate": 0.0,
            "peak_channel": 2,
            "peak_to_peak_adc": 80.0,
            "snr": 5.5,
        }
    ]
    state.unit_metrics_by_sorter = {"kilosort4": state.unit_metrics}
    save_unit_curation(
        state,
        7,
        label="candidate_single_unit",
        confidence="medium",
        checks={"waveform_shape": True, "refractory_period": True},
        notes="Stable candidate; review duplicate-template risk later.",
        reviewer="tester",
    )

    restored = load_project(save_project(state))
    record = restored.metadata["unit_curation"]["kilosort4"]["7"]

    assert record["label"] == "candidate_single_unit"
    assert record["checks"]["waveform_shape"] is True
    assert "ground truth" in record["decision_scope"]


def test_deepseek_compatible_collaborative_request_registers_tools_without_paths(
    tmp_path: Path,
):
    captured: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers["Content-Length"])
            captured["payload"] = json.loads(self.rfile.read(size))
            content = _structured_reply()
            content["tool_calls"] = [
                {
                    "name": "run_raw_qc",
                    "arguments": {"preview_seconds": 10},
                    "reason": "Establish raw-signal evidence.",
                }
            ]
            body = json.dumps(
                {
                    "id": "deepseek_mock",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(content),
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20},
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
        private_path = str(tmp_path / "private" / "recording.bin")
        settings = AISettings(
            provider="deepseek",
            base_url=f"http://127.0.0.1:{server.server_port}",
            model="deepseek-test",
            mode=AIMode.COLLABORATIVE.value,
            stream=False,
            api_key="secret-provider-key",
        )
        response = request_ai_advice(
            settings,
            question=f"Inspect {private_path}",
            task="review",
            language="en_US",
            project_summary={
                "project_open": True,
                "source_type": "binary",
                "local_only": {"recording_path": private_path},
            },
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    serialized = json.dumps(captured["payload"])
    assert captured["payload"]["tools"]
    assert captured["payload"]["thinking"] == {"type": "enabled"}
    assert captured["payload"]["reasoning_effort"] == "high"
    assert "secret-provider-key" not in serialized
    assert private_path not in serialized
    assert response.tool_calls[0]["name"] == "run_raw_qc"


def test_ollama_local_provider_does_not_require_a_secret():
    settings = AISettings(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
        model="qwen3:8b",
        api_key="",
    )

    assert settings.configured is True
    assert settings.request_api_key == "ollama"
