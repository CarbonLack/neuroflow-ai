from pathlib import Path

import numpy as np

from neuroflow.analysis import (
    event_aligned_analysis,
    match_ground_truth,
    preprocessing_preview,
    run_raw_qc,
)
from neuroflow.simulation import generate_demo_recording


def test_simulation_and_qc(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "project",
        duration_seconds=4.0,
        channel_count=16,
        sampling_rate=10_000.0,
    )
    assert state.recording_path.exists()
    assert state.recording_path.stat().st_size == 4 * 10_000 * 16 * 2
    qc = run_raw_qc(state, seconds=2.0)
    assert len(qc["channel_rms"]) == 16
    preview = preprocessing_preview(state, start_seconds=1.0, duration_seconds=0.04)
    assert preview["raw"].shape == preview["processed"].shape


def test_ground_truth_matching():
    truth = {0: np.array([0.1, 0.2, 0.3])}
    detected = {5: np.array([0.1002, 0.1998, 0.3001])}
    match = match_ground_truth(truth, detected)[0]
    assert match["truth_unit"] == 0
    assert match["f1"] == 1.0


def test_event_analysis(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "project",
        duration_seconds=6.0,
        channel_count=16,
        sampling_rate=10_000.0,
    )
    state.sorted_spikes = state.ground_truth
    result = event_aligned_analysis(state)
    assert result["population_z"].shape[0] == len(state.ground_truth)
    assert len(result["units"]) == len(state.ground_truth)
