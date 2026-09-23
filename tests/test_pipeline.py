import json
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
from neuroflow.decoding import decoding_input_diagnostics, run_decoding_suite
from neuroflow.figures import behavior_figure, event_analysis_figure, unit_cluster_figure
from neuroflow.ephys_toolkit import run_neural_toolkit
from neuroflow.models import ProjectState
from neuroflow.project import load_project, save_project
from neuroflow.simulation import generate_demo_recording, simulate_sorter_output
from neuroflow.statistics import adjust_pvalues, run_statistical_suite
from neuroflow.sorting import _attach_probe
from neuroflow.unit_curation import (
    analysis_spikes, apply_curated_single_units, curated_unit_entries,
    save_spike_selection_edit, save_unit_curation, undo_spike_selection_edit,
)


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


def test_demo_sorter_output_is_realistic_imperfect_and_reproducible(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "realistic_sorter_demo",
        duration_seconds=8.0,
        channel_count=16,
        sampling_rate=10_000.0,
    )
    first = simulate_sorter_output(
        state.ground_truth,
        state.duration_seconds,
        seed=42,
        native_id_offset=101,
    )
    second = simulate_sorter_output(
        state.ground_truth,
        state.duration_seconds,
        seed=42,
        native_id_offset=101,
    )
    assert list(first) == list(second)
    for unit_id in first:
        np.testing.assert_array_equal(first[unit_id], second[unit_id])
    assert list(first) != list(range(len(first)))
    assert any(
        len(detected) != len(state.ground_truth[source_id])
        for detected, source_id in zip(first.values(), sorted(state.ground_truth))
    )
    matches = match_ground_truth(state.ground_truth, first)
    mean_f1 = float(np.mean([row["f1"] for row in matches]))
    assert 0.65 < mean_f1 < 0.98


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
    assert event_figure.axes[0].get_ylabel() == "事件序号（每行一个事件）"
    assert legend[:2] == ["左杆开始 (n=2)", "右杆开始 (n=2)"]
    assert legend[2:] == ["基线窗", "响应窗"]
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


def test_unit_qc_does_not_invent_neighboring_electrodes(tmp_path: Path):
    state = generate_demo_recording(tmp_path / "geometry", duration_seconds=1.0,
                                    channel_count=8, sampling_rate=10_000.0)
    state.metadata.pop("contact_positions_um", None)
    state.sorted_spikes = {1: np.array([0.2, 0.4, 0.6])}
    compute_unit_metrics(state)
    diagnostic = state.unit_diagnostics[1]
    assert len(diagnostic["waveform_channels"]) == 1
    assert diagnostic["waveform_channel_selection"] == "peak_contact_only_geometry_unknown"
    assert diagnostic["waveform_alignment"] == "sorter_spike_timestamp_no_peak_realignment"
    peak = diagnostic["waveform_channels"][0]
    state.metadata["probe"] = {"contact_groups": [[peak, (peak + 1) % 8]]}
    compute_unit_metrics(state)
    assert state.unit_diagnostics[1]["waveform_channels"] == [peak, (peak + 1) % 8]
    state.metadata["probe"] = {}
    state.metadata["contact_positions_um"] = [
        [float(index * 200), 0.0] for index in range(8)
    ]
    state.metadata["contact_positions_um"][(peak + 1) % 8] = [float(peak * 200 + 20), 0.0]
    compute_unit_metrics(state)
    assert state.unit_diagnostics[1]["waveform_channel_selection"] == "recorded_contact_positions_within_50um"
    state.metadata["language"] = "en_US"
    figure = unit_cluster_figure(state, 1)
    assert len(figure.axes) == 4
    assert "individual spikes" in figure.axes[0].get_title(loc="left")
    assert "3/3 shown" in figure.axes[0].get_title(loc="left")
    assert len(figure.axes[0].collections) == 1
    assert len(figure.axes[0].collections[0].get_segments()) == 3
    assert "PCA" in figure.axes[2].get_title(loc="left")
    assert "not PCA-derived clusters" in figure._suptitle.get_text()
    state.sorted_spikes[2] = np.array([0.25, 0.45, 0.65])
    state.unit_metrics.append({"unit_id": 2, "peak_channel": peak})
    comparison = unit_cluster_figure(state, 1)
    legend = [item.get_text() for item in comparison.axes[2].get_legend().texts]
    assert legend == ["Unit 1 (3/3)", "Unit 2 (3/3)"]
    alternate = unit_cluster_figure(state, 1, pc_x=1, pc_y=3)
    assert alternate.axes[2].get_xlabel() == "PC 1"
    assert alternate.axes[2].get_ylabel() == "PC 3"
    assert [collection._neuro_unit_id for collection in alternate.axes[2].collections] == [1, 2]
    cache = {}
    unit_cluster_figure(state, 1, feature_cache=cache)
    assert len(cache) == 1
    unit_cluster_figure(state, 2, feature_cache=cache)
    assert len(cache) == 1  # Same contact reuses the raw snippets.
    for candidate in range(3, 8):
        state.sorted_spikes[candidate] = np.array([0.2 + candidate * 0.01])
        state.unit_metrics.append({"unit_id": candidate, "peak_channel": peak})
    all_candidates = unit_cluster_figure(state, 1)
    assert len(all_candidates.axes[2].collections) == 7
    state.sorted_spikes[1] = np.sort(np.tile(np.array([0.2, 0.4, 0.6]), 201))
    sampled = unit_cluster_figure(state, 1)
    assert "603/603 shown" in sampled.axes[0].get_title(loc="left")
    assert len(sampled.axes[0].collections[0].get_segments()) == 603


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


def test_curated_units_and_selected_behavior_events_drive_analysis(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "curated_tuning", duration_seconds=8.0,
        channel_count=8, sampling_rate=10_000.0,
    )
    state.sorted_spikes = {
        1: np.array([0.8, 1.1, 2.1, 3.1, 4.1, 5.1, 6.1]),
        2: np.array([0.9, 1.2, 2.2, 3.2, 4.2, 5.2, 6.2]),
    }
    state.active_sorter_key = "test_sorter"
    state.sorting_results = {"test_sorter": state.sorted_spikes.copy()}
    state.events = [
        {"time_seconds": time, "condition": condition, "analysis_role": "task_event"}
        for time, condition in ((1, "groom"), (2, "walk"), (3, "rest"),
                                (4, "groom"), (5, "walk"), (6, "rest"))
    ]
    for unit_id, label in ((1, "candidate_single_unit"), (2, "multi_unit_activity")):
        save_unit_curation(
            state, unit_id, label=label, confidence="high", checks={},
            notes="test", sorter_key="test_sorter",
        )
    save_project(state)
    cohort = apply_curated_single_units(state)
    assert cohort["unit_ids"] == [1]
    assert sorted(analysis_spikes(state)) == [1]
    assert sorted(state.sorting_results["test_sorter"]) == [1, 2]
    result = event_aligned_analysis(state, conditions=["groom", "walk"])
    assert sorted(result["units"]) == [1]
    assert result["selected_event_count"] == 4
    assert result["event_filter"]["requested_conditions"] == ["groom", "walk"]
    assert result["unit_selection"]["unit_ids"] == [1]
    save_project(state)
    restored = load_project(state.root)
    assert sorted(analysis_spikes(restored)) == [1]
    assert sorted(restored.sorting_results["test_sorter"]) == [1, 2]
    save_unit_curation(
        state, 2, label="candidate_single_unit", confidence="high",
        checks={}, notes="revised", sorter_key="test_sorter",
    )
    assert state.metadata["curated_unit_selection"]["needs_reapply"] is True
    import pytest
    with pytest.raises(RuntimeError, match="Reapply"):
        analysis_spikes(state)
    assert apply_curated_single_units(state)["unit_ids"] == [1, 2]


def test_spike_level_edits_are_non_destructive_and_undoable(tmp_path: Path):
    state = ProjectState(root=tmp_path / "spike_edit")
    original = np.arange(10, dtype=float) / 10
    state.active_sorter_key = "test_sorter"
    state.sorted_spikes = {4: original.copy(), 9: np.array([0.15, 0.55])}
    state.sorting_results = {
        "test_sorter": {4: original.copy(), 9: np.array([0.15, 0.55])}
    }

    save_spike_selection_edit(
        state, source_unit=4, source_indices=[1, 8], action="exclude"
    )
    split = save_spike_selection_edit(
        state, source_unit=4, source_indices=[2, 3], action="split",
        current_unit=4,
    )
    child = int(split["result_unit"])
    entries = curated_unit_entries(state)
    assert entries[4]["source_indices"].tolist() == [0, 4, 5, 6, 7, 9]
    assert entries[child]["source_indices"].tolist() == [2, 3]
    assert state.sorting_results["test_sorter"][4].tolist() == original.tolist()

    nested = save_spike_selection_edit(
        state, source_unit=4, source_indices=[3], action="split",
        current_unit=child,
    )
    nested_child = int(nested["result_unit"])
    assert curated_unit_entries(state)[child]["source_indices"].tolist() == [2]
    assert curated_unit_entries(state)[nested_child]["source_indices"].tolist() == [3]
    undo_spike_selection_edit(state)
    assert curated_unit_entries(state)[child]["source_indices"].tolist() == [2, 3]

    # Downstream IDs are compact 1..N, with the source IDs retained in provenance.
    compact = analysis_spikes(state)
    assert sorted(compact) == list(range(1, len(compact) + 1))
    assert set(state.metadata["analysis_unit_id_map"]["display_to_curated_unit"].values()) == {
        4, 9, child,
    }


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


def test_project_owned_recording_survives_directory_move(tmp_path: Path):
    original = tmp_path / "original_project"
    raw = original / "raw"
    raw.mkdir(parents=True)
    recording = raw / "recording.bin"
    recording.write_bytes(b"\0" * 64)
    state = ProjectState(
        root=original,
        name="portable",
        source_type="binary",
        source_path=recording,
        recording_path=recording,
        sampling_rate=1_000,
        channel_count=2,
        duration_seconds=0.016,
    )
    manifest = save_project(state)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["recording_path"] == "raw/recording.bin"

    moved = tmp_path / "moved_project"
    original.rename(moved)
    restored = load_project(moved)
    assert restored.recording_path == moved / "raw" / "recording.bin"
    assert restored.recording_path.exists()


def test_legacy_absolute_recording_recovers_from_moved_raw_copy(tmp_path: Path):
    project = tmp_path / "moved_project"
    raw = project / "raw"
    raw.mkdir(parents=True)
    recording = raw / "recording.bin"
    recording.write_bytes(b"\0" * 64)
    state = ProjectState(
        root=project,
        name="legacy portable",
        source_type="binary",
        source_path=recording,
        recording_path=recording,
        sampling_rate=1_000,
        channel_count=2,
        duration_seconds=0.016,
    )
    manifest = save_project(state)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["source_path"] = "Z:/old-computer/project/raw/recording.bin"
    payload["recording_path"] = "Z:/old-computer/project/raw/recording.bin"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    restored = load_project(project)
    assert restored.source_path == recording
    assert restored.recording_path == recording


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
    assert set(state.sorted_spikes) == {1, 2}
    assert np.isclose(state.sorted_spikes[1][0], 0.01)
    assert state.sorting_provenance["imported_kilosort"]["source_unit_id_map"] == {
        "1": 0,
        "2": 1,
    }

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


def test_event_label_fallback_preserves_benchmark_classes_for_decoding(
    tmp_path: Path,
):
    state = create_simulated_project(
        tmp_path / "label_fallback",
        electrode_type="Tetrode array (4 x 4)",
        duration_seconds=10,
        sampling_rate=10_000,
        channel_count=16,
    )
    state.sorted_spikes = state.ground_truth
    for index, event in enumerate(state.events):
        event.pop("condition", None)
        event["label"] = "lever_press" if index % 2 == 0 else "reward_delivery"
    result = event_aligned_analysis(state)
    assert set(result["conditions"]) == {"lever_press", "reward_delivery"}
    assert result["condition_diagnostics"]["event_labels"][
        "label_source_counts"
    ] == {"label": len(state.events)}
    diagnostic = decoding_input_diagnostics(state)
    assert diagnostic["status"] == "ready"
    decoded = run_decoding_suite(state, n_permutations=5)
    assert decoded["classes"] == ["lever_press", "reward_delivery"]


def test_decoding_diagnostic_explains_missing_classes(tmp_path: Path):
    state = ProjectState(root=tmp_path / "blocked")
    state.analysis = {
        "conditions": np.array(["unknown"] * 6),
        "units": {1: {}},
    }
    diagnostic = decoding_input_diagnostics(state)
    assert diagnostic["status"] == "blocked"
    assert diagnostic["class_counts"] == {"unknown": 6}
    assert "at least two usable labels" in diagnostic["message"]


def test_complete_neural_toolkit_retains_every_attached_result(tmp_path: Path):
    state = create_simulated_project(
        tmp_path / "complete_toolkit",
        electrode_type="Tetrode array (4 x 4)",
        duration_seconds=4,
        sampling_rate=10_000,
        channel_count=16,
    )
    state.sorted_spikes = state.ground_truth
    result = run_neural_toolkit(state)
    assert result["spike_train"]["rows"]
    assert result["connectivity"]
    assert result["population_dynamics"]
    assert result["population_dynamics"]["one_click_scope"]["bin_size_seconds"] == 0.02
    assert result["population_dynamics"]["one_click_scope"]["event_source"] == "current_event_analysis"
    assert result["connectivity"]["one_click_scope"]["type"] == "screening_not_exhaustive"
    assert state.spike_train_analysis["connectivity"] is result["connectivity"]
    assert (
        state.spike_train_analysis["population_dynamics"]
        is result["population_dynamics"]
    )


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
    assert set(state.sorted_spikes) == {1, 2}
    assert len(state.sorted_spikes[2]) == 3
    assert state.sorting_provenance["imported_nwb_units"]["source_unit_id_map"] == {
        "1": 10,
        "2": 20,
    }
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
