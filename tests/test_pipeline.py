from pathlib import Path

import numpy as np

from neuroflow.analysis import (
    _positive_lag_acg_counts,
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
from neuroflow.figures import behavior_figure, event_analysis_figure
from neuroflow.models import ProjectState
from neuroflow.project import load_project, save_project
from neuroflow.public_examples import (
    IBL_EID,
    open_or_create_public_example,
    public_example_status,
)
from neuroflow.simulation import generate_demo_recording
from neuroflow.statistics import adjust_pvalues, run_statistical_suite
from neuroflow.sorting import _attach_probe


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


def test_positive_lag_acg_matches_pairwise_histogram():
    spikes = np.array([0.0, 0.0005, 0.0015, 0.003, 0.050, 0.0505])
    edges_ms = np.arange(0.0, 6.0, 1.0)
    observed = _positive_lag_acg_counts(spikes, edges_ms)
    pairwise_ms = (
        spikes[np.newaxis, :] - spikes[:, np.newaxis]
    )[np.triu_indices(len(spikes), k=1)] * 1_000.0
    expected, _ = np.histogram(pairwise_ms, bins=edges_ms)
    np.testing.assert_array_equal(observed, expected)


def test_sorter_probe_keeps_independent_contacts_separate(tmp_path: Path):
    import spikeinterface as si

    recording = si.NumpyRecording(
        np.zeros((100, 4), dtype=np.int16),
        sampling_frequency=30_000.0,
    )
    state = ProjectState(
        name="independent wires",
        root=tmp_path,
        sampling_rate=30_000.0,
        channel_count=4,
        duration_seconds=100 / 30_000.0,
        dtype="int16",
        metadata={
            "probe": {
                "geometry_mode": "independent_contacts",
                "contact_count": 4,
            }
        },
    )

    attached = _attach_probe(recording, state)
    probe = attached.get_probe()

    np.testing.assert_allclose(probe.contact_positions[:, 0], [0, 1000, 2000, 3000])
    assert len(np.unique(probe.shank_ids)) == 4


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


def test_real_event_figures_use_event_semantics_and_localized_conditions(
    tmp_path: Path,
):
    state = generate_demo_recording(
        tmp_path / "event_figures",
        duration_seconds=6.0,
        channel_count=16,
        sampling_rate=10_000.0,
    )
    state.metadata["language"] = "zh_CN"
    state.sorted_spikes = state.ground_truth
    state.events = [
        {
            "time_seconds": time_seconds,
            "event_code": event_code,
            "condition": condition,
            "label": label,
            "zh_label": zh_label,
            "analysis_role": "task_event",
        }
        for time_seconds, event_code, condition, label, zh_label in [
            (1.0, 17, "left_lever_start", "Left lever start", "左杆开始"),
            (2.0, 19, "right_lever_start", "Right lever start", "右杆开始"),
            (3.0, 17, "left_lever_start", "Left lever start", "左杆开始"),
            (4.0, 19, "right_lever_start", "Right lever start", "右杆开始"),
        ]
    ]
    event_aligned_analysis(state, event_codes=[17, 19])

    event_figure = event_analysis_figure(state)
    legend = [text.get_text() for text in event_figure.axes[1].get_legend().texts]
    assert event_figure.axes[0].get_ylabel() == "事件序号"
    assert legend == ["左杆开始 (n=2)", "右杆开始 (n=2)"]
    assert event_figure.axes[3].get_title(loc="left").startswith("事件后效应")

    behavior = behavior_figure(state)
    assert behavior.axes[1].get_ylabel() == ""


def test_unit_qc_keeps_full_metrics_but_caps_plot_payload(tmp_path: Path):
    state = ProjectState(
        root=tmp_path / "large_unit_qc",
        sampling_rate=30_000,
        duration_seconds=1_800,
        channel_count=32,
    )
    spikes = np.linspace(0.1, 1_799.9, 50_001)
    state.sorted_spikes = {7: spikes}

    metrics = compute_unit_metrics(state)
    diagnostic = state.unit_diagnostics[7]

    assert metrics[0]["spike_count"] == 50_001
    assert diagnostic["isi_total_count"] == 50_000
    assert diagnostic["isi_plot_sampled"] is True
    assert len(diagnostic["isi_ms"]) == 20_000


def test_linear_acg_matches_original_bin_definition():
    spikes = np.array(
        [0.0, 0.0005, 0.001, 0.007, 0.049, 0.050, 0.0505, 0.099]
    )
    edges_ms = np.arange(0.0, 51.0, 1.0)
    expected = np.asarray(
        [
            np.sum(
                np.searchsorted(
                    spikes,
                    spikes + upper_ms / 1_000.0,
                    side="left",
                )
                - np.searchsorted(
                    spikes,
                    spikes + lower_ms / 1_000.0,
                    side="left",
                )
            )
            for lower_ms, upper_ms in zip(edges_ms[:-1], edges_ms[1:])
        ],
        dtype=int,
    )
    expected[0] -= len(spikes)

    actual = _positive_lag_acg_counts(spikes, edges_ms)

    assert np.array_equal(actual, expected)


def test_event_analysis_filters_sync_and_out_of_bounds_events(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "project",
        duration_seconds=6.0,
        channel_count=16,
        sampling_rate=10_000.0,
    )
    state.sorted_spikes = state.ground_truth
    state.events = [
        {
            "time_seconds": 1.0,
            "condition": "sync",
            "event_code": 11,
            "analysis_role": "synchronization",
        },
        {
            "time_seconds": 2.0,
            "condition": "code_1",
            "event_code": 1,
            "analysis_role": "task_event",
        },
        {
            "time_seconds": 3.0,
            "condition": "code_3",
            "event_code": 3,
            "analysis_role": "task_event",
        },
        {
            "time_seconds": 5.8,
            "condition": "code_1",
            "event_code": 1,
            "analysis_role": "task_event",
        },
    ]
    result = event_aligned_analysis(state, event_codes=[1, 3])
    assert result["selected_event_count"] == 2
    assert result["selected_event_codes"] == [1, 3]
    assert result["event_filter"]["excluded_counts"]["synchronization"] == 1
    assert result["event_filter"]["excluded_counts"]["outside_recording"] == 1


def test_event_analysis_flags_coincident_condition_timestamps(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "coincident_conditions",
        duration_seconds=6.0,
        channel_count=8,
        sampling_rate=10_000.0,
    )
    state.sorted_spikes = state.ground_truth
    state.events = [
        {
            "time_seconds": event_time,
            "condition": condition,
            "event_code": code,
            "analysis_role": "task_event",
        }
        for event_time in (1.0, 2.0, 3.0, 4.0)
        for condition, code in (("left_on", 21), ("right_on", 22))
    ]

    result = event_aligned_analysis(state, event_codes=[21, 22])

    diagnostics = result["condition_diagnostics"]
    assert diagnostics["valid_for_condition_comparison"] is False
    assert diagnostics["pairwise_timestamp_overlap"][0]["overlap_fraction"] == 1.0
    assert diagnostics["warnings"]


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


def test_project_roundtrip_restores_results_and_resume_stage(tmp_path: Path):
    state = ProjectState(
        root=tmp_path / "resumable_project",
        name="Resumable recording",
        source_type="binary",
        source_path=tmp_path / "source.bin",
        recording_path=tmp_path / "source.bin",
        sampling_rate=30_000,
        channel_count=4,
        duration_seconds=1.0,
    )
    state.source_path.write_bytes(b"\0" * 64)
    state.preprocessing = {
        "start_seconds": 0.25,
        "raw": np.array([[1.0, 2.0]]),
        "processed": np.array([[0.5, 1.5]]),
    }
    state.analysis = {
        "time": np.array([-0.1, 0.0, 0.1]),
        "population_z": np.array([[0.0, 1.0, 0.5]]),
    }
    state.statistics = {"rows": [{"unit": 1, "p_value": 0.04}]}
    state.workflow_status = {
        "import": "completed",
        "qc": "completed",
        "preprocess": "completed",
        "sorting": "completed",
    }
    state.metadata["last_open_step"] = "sorting"
    state.run_log = ["Imported own binary recording", "Preprocessing completed"]

    restored = load_project(save_project(state))

    assert restored.metadata["last_open_step"] == "sorting"
    assert restored.workflow_status["preprocess"] == "completed"
    assert restored.preprocessing["start_seconds"] == 0.25
    assert restored.preprocessing["processed"] == [[0.5, 1.5]]
    assert restored.analysis["time"] == [-0.1, 0.0, 0.1]
    assert restored.statistics["rows"][0]["p_value"] == 0.04
    assert "Preprocessing completed" in restored.run_log


def test_project_restore_does_not_recompute_event_analysis(tmp_path: Path):
    state = ProjectState(
        root=tmp_path / "analysis_restore",
        sampling_rate=30_000,
        channel_count=2,
        duration_seconds=10.0,
    )
    state.sorted_spikes = {0: np.array([1.0, 2.0])}
    state.events = [
        {"time_seconds": 2.0, "event_code": 21, "condition": "left_lever_on"},
        {"time_seconds": 4.0, "event_code": 22, "condition": "right_lever_on"},
    ]
    state.analysis = {
        "selected_event_codes": [21, 22],
        "condition_labels": ["left_lever_on", "right_lever_on"],
        "window": [-0.5, 1.0],
        "bin_size": 0.025,
        "units": {},
    }
    state.statistics = {"status": "completed"}

    restored = load_project(save_project(state))

    assert restored.analysis["selected_event_codes"] == [21, 22]
    assert restored.analysis["condition_labels"] == [
        "left_lever_on",
        "right_lever_on",
    ]
    assert restored.analysis["window"] == [-0.5, 1.0]
    assert restored.analysis["bin_size"] == 0.025


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


def test_fixed_ibl_public_example_opens_as_cached_project(tmp_path: Path):
    alf = (
        tmp_path
        / "PublicValidation"
        / "IBL"
        / "lab"
        / "Subjects"
        / "mouse"
        / "session"
        / "alf"
    )
    probe = alf / "probe00"
    probe.mkdir(parents=True)
    np.save(probe / "spikes.times.npy", np.array([0.1, 0.2, 1.1, 1.2]))
    np.save(probe / "spikes.clusters.npy", np.array([0, 1, 0, 1]))
    np.save(alf / "_ibl_trials.stimOn_times.npy", np.array([0.5, 1.5]))
    np.save(alf / "_ibl_trials.contrastLeft.npy", np.array([0.5, np.nan]))
    np.save(alf / "_ibl_trials.contrastRight.npy", np.array([np.nan, 0.5]))
    status = public_example_status(tmp_path, "ibl_bwm")
    assert status["downloaded"] is True
    assert status["project_ready"] is False
    state = open_or_create_public_example(tmp_path, "ibl_bwm")
    assert state.metadata["eid"] == IBL_EID
    assert state.metadata["public_example_key"] == "ibl_bwm"
    assert len(state.sorted_spikes) == 2
    restored = open_or_create_public_example(tmp_path, "ibl_bwm")
    assert restored.root == state.root
    assert public_example_status(tmp_path, "ibl_bwm")["project_ready"] is True
