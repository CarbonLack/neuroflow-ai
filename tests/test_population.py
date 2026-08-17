from pathlib import Path

import numpy as np

from neuroflow.models import ProjectState
from neuroflow.figures import population_dynamics_figure
from neuroflow.analysis import export_reproducible_bundle
from neuroflow.population import (
    align_spike_population,
    bin_spike_population,
    continuous_population_regression,
    order_population_activity,
    population_pca_trajectories,
    run_population_dynamics_suite,
)


def _event_locked_spikes():
    events = np.array([1.0, 2.0, 3.0, 4.0])
    return {
        10: np.concatenate([events - 0.08, events - 0.07]),
        20: np.concatenate([events + 0.02, events + 0.03]),
        30: np.concatenate([events + 0.12, events + 0.13]),
    }, events


def test_population_binning_alignment_ordering_and_pca():
    spikes, events = _event_locked_spikes()
    continuous = bin_spike_population(
        spikes,
        start_seconds=0.5,
        stop_seconds=4.5,
        bin_size_seconds=0.01,
        smoothing_sigma_seconds=0.02,
    )
    assert continuous["rates_hz"].shape == (400, 3)
    assert continuous["unit_ids"] == [10, 20, 30]

    aligned = align_spike_population(
        spikes,
        events,
        window_seconds=(-0.2, 0.2),
        bin_size_seconds=0.01,
        smoothing_sigma_seconds=0.01,
        event_labels=["left", "left", "right", "right"],
        baseline_window_seconds=(-0.2, -0.12),
        baseline_mode="subtract",
    )
    assert aligned["rates"].shape == (4, 40, 3)
    mean_activity = aligned["rates"].mean(axis=0)
    peak_times = aligned["time_seconds"][np.argmax(mean_activity, axis=0)]
    np.testing.assert_allclose(peak_times, [-0.075, 0.025, 0.125], atol=0.011)

    ordering = order_population_activity(aligned["rates"], method="peak_time")
    np.testing.assert_array_equal(ordering["unit_order_indices"], [0, 1, 2])
    pca = population_pca_trajectories(
        aligned["rates"], aligned["event_labels"], n_components=3
    )
    assert pca["conditions"].tolist() == ["left", "right"]
    assert pca["trajectories"].shape == (2, 40, 3)

    masked = align_spike_population(
        spikes,
        events[:2],
        window_seconds=(-0.2, 0.2),
        bin_size_seconds=0.01,
        smoothing_sigma_seconds=0.0,
        trial_valid_windows_seconds=[(-0.2, 0.0), (-0.2, 0.2)],
        baseline_window_seconds=(-0.2, -0.1),
        baseline_mode="subtract",
        baseline_scope="per_trial",
    )
    positive_time = masked["time_seconds"] > 0.05
    assert np.all(np.isnan(masked["rates"][0, positive_time]))
    assert np.all(np.isfinite(masked["rates"][1, positive_time]))
    baseline = (masked["time_seconds"] >= -0.2) & (
        masked["time_seconds"] < -0.1
    )
    np.testing.assert_allclose(
        np.nanmean(masked["rates"][:, baseline], axis=1),
        0.0,
        atol=1e-12,
    )


def test_population_suite_uses_explicit_state_events(tmp_path: Path):
    spikes, events = _event_locked_spikes()
    state = ProjectState(
        root=tmp_path,
        duration_seconds=5.0,
        sorted_spikes=spikes,
        events=[
            {"time_seconds": float(value), "condition": "go"}
            for value in events
        ],
    )
    result = run_population_dynamics_suite(
        state,
        window_seconds=(-0.2, 0.2),
        bin_size_seconds=0.01,
        smoothing_sigma_seconds=0.01,
        ordering_method="pca_loading",
    )
    assert result["schema"] == "neuroflow.population_aligned.v1"
    assert result["ordering"]["method"] == "pca_loading"
    assert state.spike_train_analysis["population_dynamics"] is result
    assert "4 trials" in state.run_log[-1]
    for view in ("heatmap", "single_trial", "conditions", "pca"):
        assert population_dynamics_figure(state, view).axes
    exported = export_reproducible_bundle(state, tmp_path / "export")
    assert (exported / "tables" / "population_unit_order.csv").is_file()
    assert (exported / "tables" / "population_condition_timecourse.csv").is_file()
    assert (exported / "arrays" / "population_dynamics.npz").is_file()
    assert (exported / "figures" / "population_pca.svg").is_file()


def test_continuous_regression_holds_out_trials_and_scales_neurons():
    rng = np.random.default_rng(42)
    trials, time_bins, units = 24, 80, 8
    rates = rng.normal(size=(trials, time_bins, units))
    weights = np.linspace(0.4, 1.2, units)
    target = rates @ weights + rng.normal(scale=0.15, size=(trials, time_bins))
    result = continuous_population_regression(
        rates,
        target,
        bin_size_seconds=0.01,
        target_lag_seconds=0.0,
        neuron_counts=[1, 4, 8],
        train_fraction=0.8,
        repeats=5,
        seed=7,
    )
    assert result["schema"] == "neuroflow.continuous_population_regression.v1"
    assert result["summary"][-1]["mean_r2"] > result["summary"][0]["mean_r2"]
    assert result["summary"][-1]["mean_r2"] > 0.98
    for split in result["split_records"]:
        assert not set(split["train_trial_indices"]) & set(
            split["test_trial_indices"]
        )
    assert result["configuration"]["positive_lag_definition"] == (
        "neural(t) predicts target(t + lag)"
    )
