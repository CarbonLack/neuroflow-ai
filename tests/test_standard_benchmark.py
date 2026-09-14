from __future__ import annotations

import json

from neuroflow.analysis import run_raw_qc
from neuroflow.benchmark.config import load_config
from neuroflow.benchmark.pipeline import estimate_storage, generate_session
from neuroflow.project import load_project


def _small_config():
    config = load_config()
    config["sampling_rate_hz"] = 3_000
    config["lfp_sampling_rate_hz"] = 1_000
    config["chunk_seconds"] = 2
    config["lightweight"]["duration_seconds"] = [65]
    config["lightweight"]["sessions"] = 1
    config["lightweight"]["trial_range"] = [3, 3]
    config["neuropixels"]["lightweight_channels"] = 16
    config["neuropixels"]["lightweight_units_per_region"] = {"M1": [3, 3], "mPFC": [3, 3]}
    config["tetrode"]["lightweight_channels"] = 8
    config["tetrode"]["lightweight_units_per_region"] = {"M1": [2, 2], "mPFC": [2, 2]}
    config["qc"]["transient_artifacts"] = [1, 1]
    config["qc"]["high_noise_channels"] = [1, 1]
    config["qc"]["line_noise_channels"] = [1, 1]
    return config


def test_storage_estimate_matches_full_spec():
    estimate = estimate_storage(load_config())
    assert estimate["full_neuropixels_raw_bytes"] == 64_512_000_000
    assert estimate["full_tetrode_raw_bytes"] == 16_128_000_000
    assert estimate["all_raw_bytes"] == 83_059_200_000


def test_small_session_is_deterministic_blinded_and_valid(tmp_path):
    cfg = _small_config()
    project, truth, result = generate_session(tmp_path / "first", cfg, "lightweight", "neuropixels", 0)
    assert result["passed"], result
    manifest = json.loads((project / "neuroflow_project.json").read_text(encoding="utf-8"))
    assert manifest["ground_truth_archive"] is None
    assert not (project / "derived" / "ground_truth.npz").exists()
    assert (project / "benchmark_inputs" / "blinded_candidate_sorting" / "spike_times.npy").is_file()
    assert (truth / "true_spike_times.npz").is_file()
    state = load_project(project / "neuroflow_project.json")
    qc = run_raw_qc(state)
    truth_payload = json.loads((truth / "session_ground_truth.json").read_text(encoding="utf-8"))
    plan = truth_payload["qc_plan"]
    assert set(plan["high_noise_channels"]).issubset(qc["high_noise_channels"])
    assert set(plan["dead_channels"]).issubset(qc["dead_channels"])
    assert set(plan["line_noise_channels"]).issubset(
        {index for index, label in enumerate(qc["channel_labels"]) if label == "line_noise"}
    )
    first = (project / "raw" / "recording.bin").read_bytes()
    second_project, _, second_result = generate_session(tmp_path / "second", cfg, "lightweight", "neuropixels", 0)
    assert second_result["passed"]
    assert first == (second_project / "raw" / "recording.bin").read_bytes()
