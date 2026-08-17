from pathlib import Path

import numpy as np

from neuroflow.connectivity import (
    analyze_spike_connectivity,
    cross_correlogram,
    jitter_corrected_correlogram,
    project_interval_sets,
    run_connectivity_suite,
)
from neuroflow.analysis import export_reproducible_bundle
from neuroflow.figures import connectivity_figure
from neuroflow.models import ProjectState


def _connected_spikes(seed: int = 17) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    duration = 60.0
    reference = np.sort(rng.uniform(0.1, duration - 0.1, 650))
    transmitted = reference[rng.random(len(reference)) < 0.55] + 0.002
    background = rng.uniform(0.1, duration - 0.1, 300)
    connected = np.sort(np.concatenate((transmitted, background)))
    independent = np.sort(rng.uniform(0.1, duration - 0.1, 650))
    return reference, connected, independent


def test_cross_correlogram_preserves_explicit_lag_and_units():
    reference, connected, _ = _connected_spikes()
    result = cross_correlogram(
        reference,
        connected,
        duration_seconds=60.0,
        bin_size_seconds=0.001,
        max_lag_seconds=0.02,
        normalization="reference_rate",
    )
    peak_lag = result["lags_seconds"][np.argmax(result["values"])]
    assert np.isclose(peak_lag, 0.002)
    assert result["value_unit"] == "target_spikes_per_reference_second"
    assert len(result["lags_seconds"]) == 41


def test_trial_rate_normalization_corrects_rate_and_lag_overlap():
    spikes = np.array([0.15, 0.35, 0.55, 0.75])
    result = cross_correlogram(
        spikes,
        spikes,
        duration_seconds=1.0,
        bin_size_seconds=0.1,
        max_lag_seconds=0.1,
        trial_intervals=[(0.0, 0.5), (0.5, 1.0)],
        normalization="trial_rate",
    )
    zero_index = int(np.flatnonzero(np.isclose(result["lags_seconds"], 0.0))[0])
    assert np.isclose(result["values"][zero_index], 1.0)
    assert result["value_unit"] == "dimensionless_trial_rate_normalized_ccg"
    assert result["interval_count"] == 2


def test_interval_jitter_preserves_fine_peak_and_is_reproducible():
    reference, connected, _ = _connected_spikes()
    first = jitter_corrected_correlogram(
        reference,
        connected,
        duration_seconds=60.0,
        jitter_iterations=20,
        seed=99,
    )
    second = jitter_corrected_correlogram(
        reference,
        connected,
        duration_seconds=60.0,
        jitter_iterations=20,
        seed=99,
    )
    peak_lag = first["lags_seconds"][np.argmax(first["corrected_values"])]
    assert np.isclose(peak_lag, 0.002)
    np.testing.assert_allclose(first["corrected_values"], second["corrected_values"])


def test_connectivity_suite_finds_delayed_pair_and_filters_by_region(tmp_path: Path):
    reference, connected, independent = _connected_spikes()
    spikes = {1: reference, 2: connected, 3: independent}
    result = analyze_spike_connectivity(
        spikes,
        duration_seconds=60.0,
        unit_positions_um={1: (0.0, 0.0), 2: (0.0, 40.0), 3: (0.0, 500.0)},
        unit_regions={1: "M1", 2: "M1", 3: "PMd"},
        pair_mode="within_region",
        jitter_iterations=30,
        threshold_sd=7.0,
        multiple_comparison="none",
        seed=101,
    )
    assert result["schema"] == "neuroflow.connectivity.v1"
    assert result["tested_pair_count"] == 1
    assert result["significant_pair_count"] == 1
    pair = result["pairs"][0]
    assert (pair["unit_a"], pair["unit_b"]) == (1, 2)
    assert np.isclose(pair["peak_lag_seconds"], 0.002)
    assert pair["relationship"] == "asynchronous"
    assert np.isclose(pair["distance_um"], 40.0)

    state = ProjectState(
        root=tmp_path,
        duration_seconds=60.0,
        sorted_spikes=spikes,
        unit_metrics=[
            {"unit_id": 1, "peak_channel": 0},
            {"unit_id": 2, "peak_channel": 1},
            {"unit_id": 3, "peak_channel": 2},
        ],
        metadata={
            "contact_positions_um": [[0, 0], [0, 40], [0, 500]],
            "unit_regions": {"1": "M1", "2": "M1", "3": "PMd"},
        },
    )
    state_result = run_connectivity_suite(
        state,
        pair_mode="between_regions",
        jitter_iterations=10,
        threshold_sd=7.0,
        multiple_comparison="none",
    )
    assert state_result["tested_pair_count"] == 2
    assert state.spike_train_analysis["connectivity"] is state_result
    assert "Connectivity analysis completed" in state.run_log[-1]
    for view in ("examples", "network", "distance"):
        assert connectivity_figure(state, view).axes

    # The minimal metrics above are only used to infer unit positions. Full unit
    # QC is an independent optional stage and is not required for this export.
    state.unit_metrics = []
    exported = export_reproducible_bundle(state, tmp_path / "export")
    assert (exported / "tables" / "spike_timing_connectivity.csv").is_file()
    assert (exported / "figures" / "connectivity_ccg_examples.svg").is_file()
    assert (exported / "figures" / "connectivity_network.svg").is_file()


def test_connectivity_reports_pair_truncation_and_handles_no_candidates():
    reference, connected, independent = _connected_spikes()
    spikes = {1: reference, 2: connected, 3: independent}
    truncated = analyze_spike_connectivity(
        spikes,
        duration_seconds=60.0,
        max_pairs=1,
        jitter_iterations=5,
        multiple_comparison="none",
    )
    assert truncated["candidate_pair_count"] == 3
    assert truncated["tested_pair_count"] == 1
    assert truncated["pair_selection_truncated"] is True
    assert truncated["estimated_surrogate_ccg_count"] == 5
    assert "truncated" in truncated["limitations"][-1]

    empty = analyze_spike_connectivity(
        spikes,
        duration_seconds=60.0,
        unit_regions={1: "M1"},
        pair_mode="between_regions",
        jitter_iterations=5,
    )
    assert empty["candidate_pair_count"] == 0
    assert empty["tested_pair_count"] == 0
    assert empty["pairs"] == []


def test_project_interval_sets_requires_explicit_start_and_stop(tmp_path: Path):
    state = ProjectState(
        root=tmp_path,
        events=[{"time_seconds": 1.0}, {"time_seconds": 2.0}],
        trials=[
            {"time_seconds": 1.0},
            {"start_time": 2.0, "stop_time": 3.0},
        ],
        metadata={
            "intervals": {
                "stimulus": [
                    {"start_time": 4.0, "stop_time": 4.5},
                    {"start_time": None, "stop_time": 6.0},
                ]
            }
        },
    )
    interval_sets = project_interval_sets(state)
    assert interval_sets == {
        "stimulus": [(4.0, 4.5)],
        "defined_trials": [(2.0, 3.0)],
    }
