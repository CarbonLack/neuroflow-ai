from pathlib import Path

import numpy as np

from neuroflow.analysis import (
    compute_unit_metrics,
    event_aligned_analysis,
    match_ground_truth,
    preprocessing_preview,
    run_raw_qc,
)
from neuroflow.data_import import (
    create_simulated_project,
    import_binary_recording,
    import_ibl_alf,
    import_ibl_trials_aggregate,
    import_kilosort_results,
    import_nwb_units,
)
from neuroflow.decoding import run_decoding_suite
from neuroflow.project import load_project, save_project
from neuroflow.simulation import generate_demo_recording
from neuroflow.statistics import adjust_pvalues, run_statistical_suite


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


def test_binary_import_and_project_roundtrip(tmp_path: Path):
    raw = np.arange(400, dtype=np.int16).reshape(100, 4)
    source = tmp_path / "source.bin"
    raw.tofile(source)
    state = import_binary_recording(
        tmp_path / "project",
        source,
        sampling_rate=1000,
        channel_count=4,
    )
    assert state.duration_seconds == 0.1
    restored = load_project(save_project(state))
    assert restored.recording_path == source
    assert restored.channel_count == 4


def test_kilosort_and_ibl_alf_imports(tmp_path: Path):
    ks = tmp_path / "ks"
    ks.mkdir()
    np.save(ks / "spike_times.npy", np.array([10, 20, 30, 40]))
    np.save(ks / "spike_clusters.npy", np.array([0, 0, 1, 1]))
    state = import_kilosort_results(tmp_path / "ks_project", ks, 1000)
    assert set(state.sorted_spikes) == {0, 1}
    assert np.isclose(state.sorted_spikes[0][0], 0.01)

    alf = tmp_path / "alf"
    probe = alf / "probe00" / "pykilosort"
    probe.mkdir(parents=True)
    np.save(probe / "spikes.times.npy", np.array([0.1, 0.2, 1.1, 1.2]))
    np.save(probe / "spikes.clusters.npy", np.array([0, 1, 0, 1]))
    np.save(alf / "_ibl_trials.stimOn_times.npy", np.array([0.5, 1.5]))
    np.save(alf / "_ibl_trials.contrastLeft.npy", np.array([0.5, np.nan]))
    np.save(alf / "_ibl_trials.contrastRight.npy", np.array([np.nan, 0.5]))
    ibl = import_ibl_alf(tmp_path / "ibl_project", alf)
    assert len(ibl.events) == 2
    assert {event["condition"] for event in ibl.events} == {"left", "right"}


def test_statistics_and_decoding_suite(tmp_path: Path):
    state = create_simulated_project(
        tmp_path / "project",
        electrode_type="Tetrode array (4 x 4)",
        duration_seconds=10,
        sampling_rate=10_000,
        channel_count=16,
    )
    state.sorted_spikes = state.ground_truth
    compute_unit_metrics(state)
    event_aligned_analysis(state)
    statistical = run_statistical_suite(state)
    decoding = run_decoding_suite(state, n_permutations=10)
    assert len(statistical["rows"]) == len(state.ground_truth)
    assert 0 <= decoding["balanced_accuracy"] <= 1
    assert decoding["confusion_matrix"].shape == (2, 2)
    adjusted = adjust_pvalues(np.array([0.01, 0.04, 0.2]))
    assert np.all(adjusted >= np.array([0.01, 0.04, 0.2]))


def test_ibl_aggregate_import(tmp_path: Path):
    import pandas as pd

    table = pd.DataFrame(
        {
            "eid": ["session-a"] * 4,
            "stimOn_times": [1.0, 2.0, 3.0, 4.0],
            "firstMovement_times": [1.2, 2.3, 3.25, 4.4],
            "contrastLeft": [1.0, 0.25, np.nan, np.nan],
            "contrastRight": [np.nan, np.nan, 0.25, 1.0],
            "choice": [1, 1, -1, -1],
            "bwm_include": [True] * 4,
        }
    )
    path = tmp_path / "trials.pqt"
    table.to_parquet(path)
    state = import_ibl_trials_aggregate(tmp_path / "project", path)
    assert state.metadata["eid"] == "session-a"
    assert len(state.trials) == 4
    assert {event["condition"] for event in state.events} == {"left", "right"}


def test_nwb_units_behavior_and_intervals_import(tmp_path: Path):
    import h5py

    source = tmp_path / "session.nwb"
    with h5py.File(source, "w") as handle:
        units = handle.create_group("units")
        units.create_dataset("id", data=np.array([10, 20]))
        units.create_dataset(
            "spike_times", data=np.array([0.1, 0.2, 1.1, 1.2, 1.4])
        )
        units.create_dataset("spike_times_index", data=np.array([2, 5]))
        reward = handle.create_group(
            "processing/behavior/RewardEventsEightMazeTrack"
        )
        reward.create_dataset("data", data=np.array([0, 1, 0, 1]))
        reward.create_dataset("timestamps", data=np.array([2.0, 3.0, 4.0, 5.0]))
        states = handle.create_group("processing/behavior/SleepStates")
        states.create_dataset("start_time", data=np.array([0.0, 1.0]))
        states.create_dataset("stop_time", data=np.array([1.0, 2.0]))
        states.create_dataset("label", data=np.array([b"WAKE", b"NREM"]))
        ripples = handle.create_group("processing/ecephys/Ripples")
        ripples.create_dataset("start_time", data=np.array([0.4]))
        ripples.create_dataset("stop_time", data=np.array([0.5]))
    state = import_nwb_units(tmp_path / "project", source)
    assert set(state.sorted_spikes) == {10, 20}
    assert len(state.sorted_spikes[20]) == 3
    assert {event["condition"] for event in state.events} == {
        "reward-0",
        "reward-1",
    }
    assert len(state.metadata["intervals"]["sleep_states"]) == 2
    assert len(state.metadata["intervals"]["ripples"]) == 1


def test_statistics_marks_identical_condition_values(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "constant_project",
        duration_seconds=6.0,
        channel_count=8,
        sampling_rate=10_000,
    )
    state.sorted_spikes = {0: np.array([])}
    event_aligned_analysis(state)
    result = run_statistical_suite(state)
    assert result["rows"][0]["condition_test_status"] == (
        "not_testable_all_values_identical"
    )
