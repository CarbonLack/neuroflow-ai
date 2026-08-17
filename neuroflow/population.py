from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter1d
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .models import ProjectState


POPULATION_ORDERING_METHODS = (
    {
        "key": "peak_time",
        "name": "Peak response time",
        "provider": "NeuroEphys AI",
    },
    {
        "key": "pca_loading",
        "name": "First PCA loading",
        "provider": "scikit-learn",
    },
    {
        "key": "rastermap",
        "name": "Rastermap embedding",
        "provider": "Rastermap (optional)",
    },
)

CONTINUOUS_MODELS = (
    {
        "key": "linear",
        "name": "Ordinary least squares",
        "provider": "scikit-learn",
    },
    {
        "key": "ridge",
        "name": "Standardized ridge regression",
        "provider": "scikit-learn",
    },
)


def _clean_spikes(values: np.ndarray | list[float]) -> np.ndarray:
    spikes = np.asarray(values, dtype=float).reshape(-1)
    return np.sort(spikes[np.isfinite(spikes) & (spikes >= 0)])


def _relative_edges(
    window_seconds: tuple[float, float],
    bin_size_seconds: float,
) -> np.ndarray:
    start, stop = (float(value) for value in window_seconds)
    if stop <= start:
        raise ValueError("window_seconds must have stop > start")
    if bin_size_seconds <= 0:
        raise ValueError("bin_size_seconds must be positive")
    bin_count = int(np.floor((stop - start) / bin_size_seconds + 1e-9))
    if bin_count < 2:
        raise ValueError("The requested window must contain at least two bins")
    return start + np.arange(bin_count + 1, dtype=float) * bin_size_seconds


def bin_spike_population(
    spike_trains: dict[int, np.ndarray | list[float]],
    *,
    start_seconds: float,
    stop_seconds: float,
    bin_size_seconds: float = 0.001,
    smoothing_sigma_seconds: float = 0.025,
) -> dict[str, Any]:
    """Bin and optionally Gaussian-smooth a continuous population recording."""

    edges = _relative_edges(
        (float(start_seconds), float(stop_seconds)),
        bin_size_seconds,
    )
    unit_ids = sorted(int(unit_id) for unit_id in spike_trains)
    rates = np.zeros((len(edges) - 1, len(unit_ids)), dtype=float)
    for unit_index, unit_id in enumerate(unit_ids):
        rates[:, unit_index] = (
            np.histogram(_clean_spikes(spike_trains[unit_id]), edges)[0]
            / bin_size_seconds
        )
    if smoothing_sigma_seconds < 0:
        raise ValueError("smoothing_sigma_seconds cannot be negative")
    if smoothing_sigma_seconds > 0:
        rates = gaussian_filter1d(
            rates,
            sigma=smoothing_sigma_seconds / bin_size_seconds,
            axis=0,
            mode="constant",
        )
    return {
        "schema": "neuroflow.population_continuous.v1",
        "unit_ids": unit_ids,
        "time_seconds": (edges[:-1] + edges[1:]) / 2,
        "rates_hz": rates,
        "bin_size_seconds": float(bin_size_seconds),
        "smoothing_sigma_seconds": float(smoothing_sigma_seconds),
        "analysis_start_seconds": float(edges[0]),
        "analysis_stop_seconds": float(edges[-1]),
    }


def align_spike_population(
    spike_trains: dict[int, np.ndarray | list[float]],
    event_times_seconds: np.ndarray | list[float],
    *,
    window_seconds: tuple[float, float] = (-0.5, 1.0),
    bin_size_seconds: float = 0.001,
    smoothing_sigma_seconds: float = 0.025,
    event_labels: np.ndarray | list[Any] | None = None,
    trial_valid_windows_seconds: np.ndarray | list[tuple[float, float]] | None = None,
    baseline_window_seconds: tuple[float, float] | None = None,
    baseline_mode: str = "none",
    baseline_scope: str = "pooled_units",
) -> dict[str, Any]:
    """Create independent single-trial population traces around explicit events."""

    events = np.asarray(event_times_seconds, dtype=float).reshape(-1)
    if not len(events) or not np.all(np.isfinite(events)):
        raise ValueError("event_times_seconds must contain finite event times")
    labels = (
        np.asarray(event_labels).astype(str)
        if event_labels is not None
        else np.full(len(events), "all", dtype=str)
    )
    if len(labels) != len(events):
        raise ValueError("event_labels must match event_times_seconds")
    if smoothing_sigma_seconds < 0:
        raise ValueError("smoothing_sigma_seconds cannot be negative")
    if baseline_mode not in {"none", "subtract", "zscore"}:
        raise ValueError("baseline_mode must be 'none', 'subtract', or 'zscore'")
    if baseline_scope not in {"pooled_units", "per_trial"}:
        raise ValueError("baseline_scope must be 'pooled_units' or 'per_trial'")
    if baseline_mode != "none" and baseline_window_seconds is None:
        raise ValueError("baseline_window_seconds is required for baseline correction")

    relative_edges = _relative_edges(window_seconds, bin_size_seconds)
    time_seconds = (relative_edges[:-1] + relative_edges[1:]) / 2
    unit_ids = sorted(int(unit_id) for unit_id in spike_trains)
    rates = np.zeros((len(events), len(time_seconds), len(unit_ids)), dtype=float)
    valid_time_mask = np.ones((len(events), len(time_seconds)), dtype=bool)
    if trial_valid_windows_seconds is not None:
        valid_windows = np.asarray(trial_valid_windows_seconds, dtype=float)
        if valid_windows.shape != (len(events), 2):
            raise ValueError(
                "trial_valid_windows_seconds must have one start/stop pair per event"
            )
        if np.any(~np.isfinite(valid_windows)) or np.any(
            valid_windows[:, 1] <= valid_windows[:, 0]
        ):
            raise ValueError("Every trial validity window must be finite and non-empty")
        valid_time_mask = (
            time_seconds[None, :] >= valid_windows[:, 0, None]
        ) & (time_seconds[None, :] < valid_windows[:, 1, None])
    cleaned = {
        int(unit_id): _clean_spikes(values) for unit_id, values in spike_trains.items()
    }
    for trial_index, event_time in enumerate(events):
        absolute_edges = event_time + relative_edges
        for unit_index, unit_id in enumerate(unit_ids):
            rates[trial_index, :, unit_index] = (
                np.histogram(cleaned[unit_id], absolute_edges)[0]
                / bin_size_seconds
            )
        rates[trial_index, ~valid_time_mask[trial_index], :] = 0.0
    if smoothing_sigma_seconds > 0:
        rates = gaussian_filter1d(
            rates,
            sigma=smoothing_sigma_seconds / bin_size_seconds,
            axis=1,
            mode="constant",
        )
    rates[~valid_time_mask, :] = np.nan

    baseline_summary: dict[str, Any] = {
        "mode": baseline_mode,
        "scope": baseline_scope,
    }
    if baseline_mode != "none":
        baseline_start, baseline_stop = baseline_window_seconds or (0.0, 0.0)
        baseline_mask = (time_seconds >= baseline_start) & (
            time_seconds < baseline_stop
        )
        if not np.any(baseline_mask):
            raise ValueError("baseline_window_seconds does not contain any bins")
        if np.any(~np.any(valid_time_mask[:, baseline_mask], axis=1)):
            raise ValueError(
                "Every trial must contain at least one valid bin in the baseline window"
            )
        pooled = rates[:, baseline_mask, :]
        if baseline_scope == "per_trial":
            baseline_mean = np.nanmean(pooled, axis=1)
            subtraction = baseline_mean[:, None, :]
        else:
            baseline_mean = np.nanmean(pooled, axis=(0, 1))
            subtraction = baseline_mean[None, None, :]
        baseline_summary["mean_hz"] = baseline_mean
        rates = rates - subtraction
        if baseline_mode == "zscore":
            baseline_std = (
                np.nanstd(pooled, axis=1, ddof=1)
                if baseline_scope == "per_trial"
                else np.nanstd(pooled, axis=(0, 1), ddof=1)
            )
            safe_std = np.where(baseline_std > 0, baseline_std, 1.0)
            rates = rates / (
                safe_std[:, None, :]
                if baseline_scope == "per_trial"
                else safe_std[None, None, :]
            )
            baseline_summary["std_hz"] = baseline_std
        baseline_summary["window_seconds"] = [baseline_start, baseline_stop]

    return {
        "schema": "neuroflow.population_aligned.v1",
        "unit_ids": unit_ids,
        "event_times_seconds": events,
        "event_labels": labels,
        "time_seconds": time_seconds,
        "rates": rates,
        "valid_time_mask": valid_time_mask,
        "value_unit": "z_score" if baseline_mode == "zscore" else "Hz",
        "bin_size_seconds": float(bin_size_seconds),
        "smoothing_sigma_seconds": float(smoothing_sigma_seconds),
        "window_seconds": [float(relative_edges[0]), float(relative_edges[-1])],
        "baseline": baseline_summary,
    }


def order_population_activity(
    aligned_rates: np.ndarray,
    *,
    method: str = "peak_time",
    random_state: int = 20260817,
) -> dict[str, Any]:
    """Order units from trial-averaged activity using a selectable method."""

    rates = np.asarray(aligned_rates, dtype=float)
    if rates.ndim == 3:
        mean_activity = np.nanmean(rates, axis=0)
    elif rates.ndim == 2:
        mean_activity = rates
    else:
        raise ValueError("aligned_rates must be time x unit or trial x time x unit")
    if mean_activity.shape[0] < 2 or mean_activity.shape[1] < 1:
        raise ValueError("Population activity requires at least two bins and one unit")
    centered = mean_activity - np.nanmean(mean_activity, axis=0, keepdims=True)
    scale = np.nanstd(centered, axis=0, ddof=1, keepdims=True)
    normalized = np.divide(
        centered,
        scale,
        out=np.zeros_like(centered),
        where=scale > 0,
    )
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)
    provider_version = None
    if method == "peak_time":
        score = np.argmax(normalized, axis=0).astype(float)
        order = np.argsort(score, kind="stable")
        provider = "NeuroEphys AI"
    elif method == "pca_loading":
        score = PCA(n_components=1, random_state=random_state).fit_transform(
            normalized.T
        )[:, 0]
        order = np.argsort(score, kind="stable")
        provider = "scikit-learn"
    elif method == "rastermap":
        try:
            from rastermap import Rastermap
        except (ImportError, OSError) as exc:
            raise RuntimeError(
                "Rastermap is not installed. Choose peak_time or pca_loading, or "
                "install the optional Rastermap backend."
            ) from exc
        model = Rastermap(verbose=False).fit(normalized.T)
        embedding = np.asarray(model.embedding).reshape(len(normalized.T), -1)
        score = embedding[:, 0]
        order = np.asarray(model.isort, dtype=int)
        provider = "Rastermap"
        try:
            provider_version = version("rastermap")
        except PackageNotFoundError:
            provider_version = "unknown"
    else:
        raise ValueError("method must be 'peak_time', 'pca_loading', or 'rastermap'")
    return {
        "method": method,
        "provider": provider,
        "provider_version": provider_version,
        "unit_order_indices": np.asarray(order, dtype=int),
        "ordering_score": np.asarray(score, dtype=float),
        "normalized_mean_activity": normalized,
    }


def population_pca_trajectories(
    aligned_rates: np.ndarray,
    event_labels: np.ndarray | list[Any] | None = None,
    *,
    n_components: int = 3,
    standardize_units: bool = True,
) -> dict[str, Any]:
    rates = np.asarray(aligned_rates, dtype=float)
    if rates.ndim != 3:
        raise ValueError("aligned_rates must be trial x time x unit")
    labels = (
        np.asarray(event_labels).astype(str)
        if event_labels is not None
        else np.full(rates.shape[0], "all", dtype=str)
    )
    if len(labels) != rates.shape[0]:
        raise ValueError("event_labels must match the trial dimension")
    conditions = np.unique(labels)
    condition_means = np.stack(
        [np.nanmean(rates[labels == condition], axis=0) for condition in conditions]
    )
    flattened = np.nan_to_num(
        condition_means.reshape(-1, rates.shape[2]),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )
    if standardize_units:
        flattened = StandardScaler().fit_transform(flattened)
    components = min(int(n_components), *flattened.shape)
    if components < 1:
        raise ValueError("At least one PCA component is required")
    pca = PCA(n_components=components)
    transformed = pca.fit_transform(flattened)
    trajectories = transformed.reshape(
        len(conditions), rates.shape[1], components
    )
    return {
        "conditions": conditions,
        "trajectories": trajectories,
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "components": pca.components_,
        "standardize_units": bool(standardize_units),
    }


def _continuous_model(model: str, ridge_alpha: float):
    if model == "linear":
        return LinearRegression()
    if model == "ridge":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=float(ridge_alpha))),
            ]
        )
    raise ValueError("model must be 'linear' or 'ridge'")


def _lagged_arrays(
    neural_rates: np.ndarray,
    target_values: np.ndarray,
    lag_bins: int,
) -> tuple[np.ndarray, np.ndarray]:
    if lag_bins > 0:
        return neural_rates[:, :-lag_bins, :], target_values[:, lag_bins:, :]
    if lag_bins < 0:
        return neural_rates[:, -lag_bins:, :], target_values[:, :lag_bins, :]
    return neural_rates, target_values


def continuous_population_regression(
    neural_rates: np.ndarray,
    target_values: np.ndarray,
    *,
    bin_size_seconds: float,
    target_lag_seconds: float = 0.0,
    neuron_counts: list[int] | np.ndarray | None = None,
    model: str = "linear",
    ridge_alpha: float = 1.0,
    train_fraction: float = 0.8,
    repeats: int = 10,
    seed: int = 20260817,
) -> dict[str, Any]:
    """Predict a continuous signal with trial-held-out population models.

    Input shape is trial x time x unit. A positive target lag means activity at
    time ``t`` predicts the target at ``t + lag``. Trials, never individual time
    bins, are assigned to train or test sets.
    """

    rates = np.asarray(neural_rates, dtype=float)
    target = np.asarray(target_values, dtype=float)
    if rates.ndim != 3:
        raise ValueError("neural_rates must be trial x time x unit")
    if target.ndim == 2:
        target = target[:, :, None]
    if target.ndim != 3 or target.shape[:2] != rates.shape[:2]:
        raise ValueError("target_values must match the trial and time dimensions")
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between zero and one")
    if repeats < 1:
        raise ValueError("repeats must be positive")
    if rates.shape[0] < 3:
        raise ValueError("At least three trials are required")
    if bin_size_seconds <= 0:
        raise ValueError("bin_size_seconds must be positive")
    lag_bins = int(np.rint(target_lag_seconds / bin_size_seconds))
    if abs(lag_bins) >= rates.shape[1] - 1:
        raise ValueError("The requested target lag leaves fewer than two time bins")
    rates, target = _lagged_arrays(rates, target, lag_bins)
    unit_count = rates.shape[2]
    if neuron_counts is None:
        suggested = [1, 2, 5, 10, 25, 50, 100, unit_count]
        counts = sorted({value for value in suggested if 0 < value <= unit_count})
    else:
        counts = sorted({int(value) for value in neuron_counts})
        if not counts or counts[0] < 1 or counts[-1] > unit_count:
            raise ValueError("neuron_counts must be within the available unit count")
    train_trial_count = int(np.floor(rates.shape[0] * train_fraction))
    train_trial_count = min(max(train_trial_count, 1), rates.shape[0] - 1)
    rng = np.random.default_rng(seed)
    rows = []
    split_records = []
    for retained in counts:
        for repeat in range(repeats):
            permutation = rng.permutation(rates.shape[0])
            train_trials = np.sort(permutation[:train_trial_count])
            test_trials = np.sort(permutation[train_trial_count:])
            selected_units = np.sort(rng.choice(unit_count, retained, replace=False))
            x_train = rates[train_trials][:, :, selected_units].reshape(-1, retained)
            y_train = target[train_trials].reshape(-1, target.shape[2])
            x_test = rates[test_trials][:, :, selected_units].reshape(-1, retained)
            y_test = target[test_trials].reshape(-1, target.shape[2])
            train_finite = np.all(np.isfinite(x_train), axis=1) & np.all(
                np.isfinite(y_train), axis=1
            )
            test_finite = np.all(np.isfinite(x_test), axis=1) & np.all(
                np.isfinite(y_test), axis=1
            )
            if np.count_nonzero(train_finite) < 2 or np.count_nonzero(test_finite) < 2:
                raise ValueError("Finite training and test samples are required")
            estimator = _continuous_model(model, ridge_alpha)
            estimator.fit(x_train[train_finite], y_train[train_finite])
            predicted = np.asarray(estimator.predict(x_test[test_finite]))
            if predicted.ndim == 1:
                predicted = predicted[:, None]
            observed = y_test[test_finite]
            component_r2 = [
                r2_score(observed[:, index], predicted[:, index])
                for index in range(observed.shape[1])
            ]
            component_correlation = []
            for index in range(observed.shape[1]):
                if (
                    np.std(observed[:, index]) == 0
                    or np.std(predicted[:, index]) == 0
                ):
                    component_correlation.append(np.nan)
                else:
                    component_correlation.append(
                        float(np.corrcoef(observed[:, index], predicted[:, index])[0, 1])
                    )
            rows.append(
                {
                    "neuron_count": retained,
                    "repeat": repeat,
                    "r2": float(np.mean(component_r2)),
                    "correlation": float(np.nanmean(component_correlation)),
                    "mae": float(mean_absolute_error(observed, predicted)),
                }
            )
            split_records.append(
                {
                    "neuron_count": retained,
                    "repeat": repeat,
                    "train_trial_indices": train_trials.tolist(),
                    "test_trial_indices": test_trials.tolist(),
                    "selected_unit_indices": selected_units.tolist(),
                }
            )
    summary = []
    for retained in counts:
        selected = [row for row in rows if row["neuron_count"] == retained]
        summary.append(
            {
                "neuron_count": retained,
                "mean_r2": float(np.mean([row["r2"] for row in selected])),
                "std_r2": float(np.std([row["r2"] for row in selected], ddof=1))
                if len(selected) > 1
                else 0.0,
                "mean_correlation": float(
                    np.mean([row["correlation"] for row in selected])
                ),
                "std_correlation": float(
                    np.std([row["correlation"] for row in selected], ddof=1)
                )
                if len(selected) > 1
                else 0.0,
                "mean_mae": float(np.mean([row["mae"] for row in selected])),
            }
        )
    return {
        "schema": "neuroflow.continuous_population_regression.v1",
        "configuration": {
            "model": model,
            "ridge_alpha": float(ridge_alpha),
            "bin_size_seconds": float(bin_size_seconds),
            "target_lag_seconds": float(target_lag_seconds),
            "lag_bins": lag_bins,
            "positive_lag_definition": "neural(t) predicts target(t + lag)",
            "train_fraction": float(train_fraction),
            "repeats": int(repeats),
            "seed": int(seed),
        },
        "trial_count": int(rates.shape[0]),
        "time_bin_count": int(rates.shape[1]),
        "available_unit_count": int(unit_count),
        "target_dimension": int(target.shape[2]),
        "rows": rows,
        "summary": summary,
        "split_records": split_records,
        "leakage_checks": [
            "Entire trials, not time bins, are held out together.",
            "Unit subsets are selected without target information.",
            "Standardization for ridge regression is fitted on training samples only.",
        ],
    }


def run_population_dynamics_suite(
    state: ProjectState,
    *,
    event_times_seconds: np.ndarray | list[float] | None = None,
    event_labels: np.ndarray | list[Any] | None = None,
    unit_ids: list[int] | np.ndarray | None = None,
    ordering_method: str = "peak_time",
    **alignment_settings: Any,
) -> dict[str, Any]:
    if not state.sorted_spikes:
        raise RuntimeError("Population dynamics requires sorted spike times")
    if event_times_seconds is None:
        event_times_seconds = [float(row["time_seconds"]) for row in state.events]
        if event_labels is None:
            event_labels = [
                str(row.get("condition", row.get("event", row.get("code", "all"))))
                for row in state.events
            ]
    selected_spikes = state.sorted_spikes
    if unit_ids is not None:
        requested = [int(unit_id) for unit_id in unit_ids]
        missing = sorted(set(requested) - set(state.sorted_spikes))
        if missing:
            raise ValueError(f"Unknown unit IDs: {missing}")
        if not requested:
            raise ValueError("unit_ids cannot be empty")
        selected_spikes = {
            unit_id: state.sorted_spikes[unit_id] for unit_id in requested
        }
    aligned = align_spike_population(
        selected_spikes,
        event_times_seconds,
        event_labels=event_labels,
        **alignment_settings,
    )
    ordering = order_population_activity(
        aligned["rates"],
        method=ordering_method,
    )
    pca = population_pca_trajectories(
        aligned["rates"], aligned["event_labels"]
    )
    result = {
        **aligned,
        "ordering": ordering,
        "pca": pca,
    }
    state.spike_train_analysis["population_dynamics"] = result
    state.log(
        "Population dynamics completed: "
        f"{len(aligned['event_times_seconds'])} trials, "
        f"{len(aligned['unit_ids'])} units, ordering={ordering_method}"
    )
    return result
