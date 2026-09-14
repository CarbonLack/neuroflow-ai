from __future__ import annotations

import json

import numpy as np

from neuroflow.analysis import run_raw_qc
from neuroflow.benchmark.config import load_config
from neuroflow.benchmark.pipeline import estimate_storage, generate_session
from neuroflow.benchmark.waveform_generator import generate_templates
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


def test_waveform_population_stays_in_real_calibration_range():
    units = [
        {
            "unit_id": unit_id,
            "firing_phenotype": "fast-spiking-like" if unit_id % 4 == 0 else "regular",
            "sorting_difficulty": "low_snr" if unit_id % 7 == 0 else "standard",
            "peak_channel": (unit_id % 8) * 4 + unit_id % 4,
        }
        for unit_id in range(80)
    ]
    templates = generate_templates(np.random.default_rng(20260915), units, "tetrode", 32, 30_000.0)
    half_widths = []
    trough_to_peaks = []
    rebound_ratios = []
    for payload in templates.values():
        waveform = payload["waveform_uv"]
        peak_channel = int(np.argmax(np.ptp(waveform, axis=0)))
        trace = waveform[:, peak_channel]
        trough_index = int(np.argmin(trace))
        trough = -float(trace[trough_index])
        threshold = -0.5 * trough
        selected = np.flatnonzero(trace <= threshold)
        half_widths.append(len(selected) / 30_000.0 * 1_000.0)
        positive_index = trough_index + 1 + int(np.argmax(trace[trough_index + 1 :]))
        trough_to_peaks.append((positive_index - trough_index) / 30_000.0 * 1_000.0)
        rebound_ratios.append(float(trace[positive_index]) / trough)
    # Broad acceptance bands are based on the 10--90% ranges measured by the
    # read-only real-data calibration; the separate report tracks exact values.
    assert 0.16 <= np.median(half_widths) <= 0.25
    assert 0.45 <= np.median(trough_to_peaks) <= 0.58
    assert 0.16 <= np.median(rebound_ratios) <= 0.29
