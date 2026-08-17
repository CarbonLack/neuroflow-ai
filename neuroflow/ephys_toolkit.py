from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import neo
import numpy as np
import quantities as pq
from elephant.conversion import BinnedSpikeTrain
from elephant.phase_analysis import mean_phase_vector, spike_triggered_phase
from elephant.signal_processing import hilbert
from elephant.spectral import welch_coherence, welch_psd
from elephant.spike_train_correlation import (
    correlation_coefficient,
    cross_correlation_histogram,
)
from elephant.spike_train_dissimilarity import (
    van_rossum_distance,
    victor_purpura_distance,
)
from elephant.statistics import cv, cv2, fanofactor, isi, lv, lvr, mean_firing_rate
from scipy import signal

from .analysis import event_aligned_analysis, load_recording
from .models import ProjectState

METHOD_CATALOG = (
    {
        "key": "spike_statistics",
        "stage": "spike_train",
        "provider": "Elephant",
        "methods": "rate, ISI, CV, CV2, Lv, LvR, trial Fano factor",
        "status": "integrated",
        "requires": "sorted spike times",
    },
    {
        "key": "spike_relationships",
        "stage": "spike_train",
        "provider": "Elephant",
        "methods": "correlation, CCH, STTC, Victor-Purpura, van Rossum",
        "status": "integrated",
        "requires": "at least two sorted units",
    },
    {
        "key": "fine_timing_connectivity",
        "stage": "connectivity",
        "provider": "NeuroEphys AI",
        "methods": (
            "count or trial/rate/edge-normalized CCG, interval-jitter correction, "
            "flank-SD or empirical significance"
        ),
        "status": "integrated",
        "requires": "simultaneously recorded sorted units and an explicit duration",
    },
    {
        "key": "single_trial_population",
        "stage": "population",
        "provider": "NeuroEphys AI + scikit-learn + optional Rastermap",
        "methods": (
            "configurable binning/Gaussian smoothing, baseline correction, "
            "single-trial activity, peak/PCA/Rastermap ordering, PCA trajectories, "
            "trial-held-out continuous regression"
        ),
        "status": "integrated",
        "requires": "sorted spike times and explicit events or trial-aligned arrays",
    },
    {
        "key": "lfp_spectral",
        "stage": "lfp",
        "provider": "Elephant + SciPy",
        "methods": "Welch PSD, coherence, phase lag, spectrogram, band power",
        "status": "integrated",
        "requires": "raw voltage and two usable channels",
    },
    {
        "key": "spike_field",
        "stage": "combined",
        "provider": "Elephant + NeuroEphys AI",
        "methods": "spike-triggered phase, mean phase vector, surrogate test, PAC",
        "status": "integrated",
        "requires": "raw voltage and sorted spike times",
    },
    {
        "key": "advanced_patterns",
        "stage": "spike_train",
        "provider": "Elephant",
        "methods": "SPADE, ASSET, UE, CAD, CuBIC, GPFA",
        "status": "catalogued",
        "requires": "task-specific validation and larger datasets",
    },
)


SOURCES = (
    {
        "name": "SpikeInterface preprocessing",
        "url": "https://spikeinterface.readthedocs.io/en/stable/modules/preprocessing.html",
        "use": "lazy preprocessing chains, bad-channel handling, referencing safeguards",
    },
    {
        "name": "SpikeInterface postprocessing",
        "url": "https://spikeinterface.readthedocs.io/en/stable/modules/postprocessing.html",
        "use": "SortingAnalyzer extensions and dependency-aware postprocessing",
    },
    {
        "name": "Neo data model",
        "url": "https://neo.readthedocs.io/en/stable/read_and_analyze.html",
        "use": "unit-aware AnalogSignal, SpikeTrain, Event, Epoch, Block and Segment objects",
    },
    {
        "name": "Elephant function reference",
        "url": "https://elephant.readthedocs.io/en/stable/modules.html",
        "use": "spike-train, spectral, synchrony and spike-field analysis APIs",
    },
    {
        "name": "Folschweiller and Sauer, 2023",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10312056/",
        "use": "respiration/LFP/spike analysis case-study structure",
    },
)


def provider_status() -> dict[str, str | bool]:
    try:
        elephant_version = version("elephant")
    except PackageNotFoundError:
        return {
            "available": False,
            "elephant": "not installed",
            "neo": version("neo"),
            "quantities": version("quantities"),
        }
    return {
        "available": True,
        "elephant": elephant_version,
        "neo": version("neo"),
        "quantities": version("quantities"),
    }


def to_neo_spike_trains(state: ProjectState) -> tuple[list[int], list[neo.SpikeTrain]]:
    unit_ids = sorted(state.sorted_spikes)
    trains = [
        neo.SpikeTrain(
            np.asarray(state.sorted_spikes[unit_id], dtype=float) * pq.s,
            t_start=0 * pq.s,
            t_stop=max(state.duration_seconds, 1e-6) * pq.s,
            name=f"Unit {unit_id}",
            unit_id=int(unit_id),
        )
        for unit_id in unit_ids
    ]
    return unit_ids, trains


def _usable_channels(state: ProjectState, count: int = 2) -> list[int]:
    bad = {int(item) for item in state.qc.get("bad_channels", [])}
    channels = [
        channel for channel in range(state.channel_count) if channel not in bad
    ]
    if len(channels) < count:
        channels = list(range(min(state.channel_count, count)))
    return channels[:count]


def to_neo_analog_signal(
    state: ProjectState,
    *,
    channels: list[int] | None = None,
    target_rate_hz: float = 1_000.0,
    max_seconds: float = 30.0,
) -> tuple[neo.AnalogSignal, list[int]]:
    if not state.ready:
        raise RuntimeError("Raw voltage is required for LFP and spike-field analysis")
    acquisition = state.metadata.get("acquisition_preprocessing", {})
    if not acquisition.get("lfp_available", True):
        raise RuntimeError(
            acquisition.get(
                "lfp_unavailable_reason",
                "The linked source does not contain an analyzable LFP band.",
            )
        )
    selected = channels or _usable_channels(state, 2)
    raw = load_recording(state)
    samples = min(raw.shape[0], int(max_seconds * state.sampling_rate))
    traces = (
        np.asarray(raw[:samples, selected], dtype=np.float32)
        * state.scale_uv_per_bit
    )
    traces -= np.median(traces, axis=0, keepdims=True)
    if state.sampling_rate > target_rate_hz:
        divisor = round(state.sampling_rate / target_rate_hz)
        if np.isclose(state.sampling_rate / divisor, target_rate_hz):
            traces = signal.resample_poly(traces, up=1, down=divisor, axis=0)
            actual_rate = state.sampling_rate / divisor
        else:
            target_samples = round(len(traces) * target_rate_hz / state.sampling_rate)
            traces = signal.resample(traces, target_samples, axis=0)
            actual_rate = target_rate_hz
    else:
        actual_rate = state.sampling_rate
    analog = neo.AnalogSignal(
        traces,
        units=pq.uV,
        sampling_rate=actual_rate * pq.Hz,
        name="NeuroEphys AI LFP proxy",
        channel_ids=np.asarray(selected, dtype=int),
    )
    return analog, selected


def _trial_fano_factor(
    spike_times: np.ndarray,
    events: list[dict],
    window: tuple[float, float] = (-0.5, 1.0),
) -> float:
    if not events:
        return float("nan")
    duration = window[1] - window[0]
    trials = []
    spike_times = np.asarray(spike_times, dtype=float)
    spike_times = np.sort(spike_times[np.isfinite(spike_times)])
    for event in events:
        event_time = float(event["time_seconds"])
        absolute_start = event_time + window[0]
        absolute_stop = event_time + window[1]
        first = np.searchsorted(spike_times, absolute_start, side="left")
        last = np.searchsorted(spike_times, absolute_stop, side="right")
        relative = spike_times[first:last] - absolute_start
        trials.append(
            neo.SpikeTrain(relative * pq.s, t_start=0 * pq.s, t_stop=duration * pq.s)
        )
    return float(fanofactor(trials)) if trials else float("nan")


def _tiled_time_fraction(
    spikes: np.ndarray,
    dt_seconds: float,
    start_seconds: float,
    stop_seconds: float,
) -> float:
    if not len(spikes) or stop_seconds <= start_seconds:
        return 0.0
    starts = np.maximum(spikes - dt_seconds, start_seconds)
    stops = np.minimum(spikes + dt_seconds, stop_seconds)
    valid = stops > starts
    starts = starts[valid]
    stops = stops[valid]
    if not len(starts):
        return 0.0
    total = 0.0
    current_start = float(starts[0])
    current_stop = float(stops[0])
    for start, stop in zip(starts[1:], stops[1:]):
        if start <= current_stop:
            current_stop = max(current_stop, float(stop))
        else:
            total += current_stop - current_start
            current_start = float(start)
            current_stop = float(stop)
    total += current_stop - current_start
    return float(total / (stop_seconds - start_seconds))


def _spike_proportion_near(
    source: np.ndarray,
    target: np.ndarray,
    dt_seconds: float,
) -> float:
    if not len(source) or not len(target):
        return 0.0
    left = np.searchsorted(target, source - dt_seconds, side="left")
    right = np.searchsorted(target, source + dt_seconds, side="right")
    return float(np.mean(right > left))


def _linear_sttc(
    first: np.ndarray,
    second: np.ndarray,
    *,
    dt_seconds: float,
    start_seconds: float,
    stop_seconds: float,
) -> float:
    """Compute the Cutts-Eglen STTC without an all-spike-pairs matrix."""
    if not len(first) or not len(second):
        return float("nan")
    pa = _spike_proportion_near(first, second, dt_seconds)
    pb = _spike_proportion_near(second, first, dt_seconds)
    ta = _tiled_time_fraction(
        first,
        dt_seconds,
        start_seconds,
        stop_seconds,
    )
    tb = _tiled_time_fraction(
        second,
        dt_seconds,
        start_seconds,
        stop_seconds,
    )

    def term(proportion: float, tiled: float) -> float:
        denominator = 1.0 - proportion * tiled
        if abs(denominator) < 1e-12:
            return 1.0
        return (proportion - tiled) / denominator

    return float(0.5 * (term(pa, tb) + term(pb, ta)))


def run_spike_train_suite(
    state: ProjectState,
    bin_ms: float = 20.0,
    distance_window_seconds: float = 10.0,
) -> dict:
    if not state.sorted_spikes:
        raise RuntimeError("Spike-train analysis requires sorting results")
    unit_ids, trains = to_neo_spike_trains(state)
    rows = []
    analysis_events = [
        {"time_seconds": float(value)}
        for value in np.asarray(
            state.analysis.get("event_times", []),
            dtype=float,
        )
    ]
    fano_events = analysis_events or [
        event
        for event in state.events
        if 0 <= float(event.get("time_seconds", -1)) <= state.duration_seconds
        and event.get("analysis_role") != "synchronization"
    ]
    for unit_id, train in zip(unit_ids, trains):
        intervals = isi(train).rescale(pq.s).magnitude
        row = {
            "unit_id": int(unit_id),
            "rate_hz": float(mean_firing_rate(train).rescale(pq.Hz).magnitude),
            "isi_cv": float(cv(intervals)) if intervals.size >= 2 else float("nan"),
            "cv2": float(cv2(intervals)) if intervals.size >= 2 else float("nan"),
            "lv": float(lv(intervals)) if intervals.size >= 2 else float("nan"),
            "lvr": (
                float(lvr(intervals * pq.s, R=5 * pq.ms))
                if intervals.size >= 2
                else float("nan")
            ),
            "fano_trials": _trial_fano_factor(
                np.asarray(state.sorted_spikes[unit_id], dtype=float),
                fano_events,
            ),
        }
        rows.append(row)

    binned = BinnedSpikeTrain(trains, bin_size=bin_ms * pq.ms)
    correlation = np.asarray(correlation_coefficient(binned), dtype=float)
    sttc = np.eye(len(trains), dtype=float)
    for i in range(len(trains)):
        for j in range(i + 1, len(trains)):
            value = _linear_sttc(
                np.asarray(state.sorted_spikes[unit_ids[i]], dtype=float),
                np.asarray(state.sorted_spikes[unit_ids[j]], dtype=float),
                dt_seconds=0.005,
                start_seconds=0.0,
                stop_seconds=state.duration_seconds,
            )
            sttc[i, j] = sttc[j, i] = float(value)

    distance_stop = min(
        max(float(distance_window_seconds), 0.1),
        state.duration_seconds,
    )
    subset_ids = unit_ids[: min(8, len(unit_ids))]
    subset = [
        neo.SpikeTrain(
            np.asarray(state.sorted_spikes[unit_id], dtype=float)[
                np.asarray(state.sorted_spikes[unit_id], dtype=float) <= distance_stop
            ]
            * pq.s,
            t_start=0 * pq.s,
            t_stop=distance_stop * pq.s,
        )
        for unit_id in subset_ids
    ]
    vp_distance = np.asarray(
        victor_purpura_distance(subset, cost_factor=10 * pq.Hz), dtype=float
    )
    vr_distance = np.asarray(
        van_rossum_distance(subset, time_constant=100 * pq.ms), dtype=float
    )
    cch = {"lags_ms": np.array([]), "counts": np.array([]), "pair": []}
    if len(trains) >= 2:
        first = BinnedSpikeTrain([trains[0]], bin_size=5 * pq.ms)
        second = BinnedSpikeTrain([trains[1]], bin_size=5 * pq.ms)
        histogram, lag_bins = cross_correlation_histogram(
            first, second, window=[-20, 20], border_correction=True
        )
        cch = {
            "lags_ms": np.asarray(lag_bins, dtype=float) * 5.0,
            "counts": np.asarray(histogram.magnitude, dtype=float).ravel(),
            "pair": [int(unit_ids[0]), int(unit_ids[1])],
        }
    result = {
        "provider": provider_status(),
        "unit_ids": unit_ids,
        "rows": rows,
        "bin_ms": float(bin_ms),
        "correlation": correlation,
        "sttc": sttc,
        "distance_unit_ids": unit_ids[: len(subset)],
        "distance_window_seconds": float(distance_stop),
        "distance_window_note": (
            "Victor-Purpura and van Rossum distances use a bounded window to "
            "avoid quadratic memory growth on long, high-rate recordings."
        ),
        "victor_purpura": vp_distance,
        "van_rossum": vr_distance,
        "cch": cch,
    }
    state.spike_train_analysis = result
    state.log(
        f"Elephant spike-train analysis completed for {len(unit_ids)} units "
        f"at {bin_ms:g} ms bins"
    )
    return result


def _band_power(frequencies: np.ndarray, psd: np.ndarray) -> dict[str, list[float]]:
    bands = {
        "delta": (1.0, 4.0),
        "theta": (4.0, 12.0),
        "beta": (12.0, 30.0),
        "low_gamma": (30.0, 80.0),
        "high_gamma": (80.0, 120.0),
    }
    result = {}
    for name, (low, high) in bands.items():
        mask = (frequencies >= low) & (frequencies < high)
        result[name] = (
            np.trapezoid(psd[:, mask], frequencies[mask], axis=1).tolist()
            if np.count_nonzero(mask) >= 2
            else [float("nan")] * psd.shape[0]
        )
    return result


def run_lfp_suite(state: ProjectState) -> dict:
    analog, channels = to_neo_analog_signal(state)
    frequencies, psd = welch_psd(
        analog,
        frequency_resolution=0.5 * pq.Hz,
        overlap=0.5,
    )
    frequency_values = np.asarray(frequencies.rescale(pq.Hz).magnitude, dtype=float)
    psd_values = np.asarray(psd.magnitude, dtype=float)
    if psd_values.ndim == 1:
        psd_values = psd_values[None, :]
    if len(channels) >= 2:
        coh_frequencies, coherence, phase_lag = welch_coherence(
            analog[:, 0],
            analog[:, 1],
            frequency_resolution=0.5 * pq.Hz,
            overlap=0.5,
        )
        coherence_values = np.asarray(coherence, dtype=float).squeeze()
        phase_values = np.asarray(phase_lag, dtype=float).squeeze()
        coherence_frequency_values = np.asarray(
            coh_frequencies.rescale(pq.Hz).magnitude, dtype=float
        )
    else:
        coherence_frequency_values = frequency_values
        coherence_values = np.zeros_like(frequency_values)
        phase_values = np.zeros_like(frequency_values)
    fs = float(analog.sampling_rate.rescale(pq.Hz).magnitude)
    spectrogram_f, spectrogram_t, spectrogram_power = signal.spectrogram(
        np.asarray(analog[:, 0].magnitude, dtype=float).ravel(),
        fs=fs,
        nperseg=min(int(2 * fs), len(analog)),
        noverlap=min(int(fs), max(len(analog) - 1, 0)),
        scaling="density",
    )
    result = {
        "provider": provider_status(),
        "channel_ids": channels,
        "sampling_rate_hz": fs,
        "duration_seconds": len(analog) / fs,
        "frequencies_hz": frequency_values,
        "psd": psd_values,
        "band_power": _band_power(frequency_values, psd_values),
        "coherence_frequencies_hz": coherence_frequency_values,
        "coherence": coherence_values,
        "phase_lag_rad": phase_values,
        "spectrogram_frequencies_hz": spectrogram_f,
        "spectrogram_times_s": spectrogram_t,
        "spectrogram_power": spectrogram_power,
    }
    state.lfp_analysis = result
    state.log(
        "Elephant LFP analysis completed: Welch PSD, coherence, phase lag, "
        "spectrogram, and band power"
    )
    return result


def _rayleigh_p_value(vector_strength: float, sample_count: int) -> float:
    if sample_count <= 0 or not np.isfinite(vector_strength):
        return float("nan")
    z = sample_count * vector_strength**2
    p_value = np.exp(
        np.sqrt(1.0 + 4.0 * sample_count + 4.0 * (sample_count**2 - z**2))
        - (1.0 + 2.0 * sample_count)
    )
    if sample_count < 50:
        p_value *= (
            1.0
            + (2.0 * z - z**2) / (4.0 * sample_count)
            - (
                24.0 * z
                - 132.0 * z**2
                + 76.0 * z**3
                - 9.0 * z**4
            )
            / (288.0 * sample_count**2)
        )
    return float(np.clip(p_value, 0.0, 1.0))


def _phase_amplitude_coupling(
    values: np.ndarray,
    fs: float,
    phase_band: tuple[float, float] = (1.0, 5.0),
    amplitude_band: tuple[float, float] = (80.0, 100.0),
    bins: int = 18,
) -> dict:
    phase_sos = signal.butter(3, phase_band, btype="bandpass", fs=fs, output="sos")
    amplitude_high = min(amplitude_band[1], fs * 0.45)
    if amplitude_high <= amplitude_band[0]:
        return {
            "phase_centers": np.linspace(-np.pi, np.pi, bins, endpoint=False),
            "normalized_amplitude": np.full(bins, 1.0 / bins),
            "kld": float("nan"),
        }
    amplitude_sos = signal.butter(
        3,
        (amplitude_band[0], amplitude_high),
        btype="bandpass",
        fs=fs,
        output="sos",
    )
    phase = np.angle(signal.hilbert(signal.sosfiltfilt(phase_sos, values)))
    amplitude = np.abs(signal.hilbert(signal.sosfiltfilt(amplitude_sos, values)))
    edges = np.linspace(-np.pi, np.pi, bins + 1)
    means = np.array(
        [
            np.nanmean(amplitude[(phase >= edges[index]) & (phase < edges[index + 1])])
            for index in range(bins)
        ],
        dtype=float,
    )
    means = np.nan_to_num(means, nan=0.0)
    normalized = means / max(means.sum(), np.finfo(float).eps)
    uniform = 1.0 / bins
    positive = normalized > 0
    kld = float(np.sum(normalized[positive] * np.log(normalized[positive] / uniform)))
    return {
        "phase_centers": (edges[:-1] + edges[1:]) / 2,
        "normalized_amplitude": normalized,
        "kld": kld,
    }


def run_spike_field_suite(
    state: ProjectState,
    phase_band: tuple[float, float] = (1.0, 5.0),
    surrogate_count: int = 200,
) -> dict:
    if not state.sorted_spikes:
        raise RuntimeError("Spike-field analysis requires sorting results")
    analog, channels = to_neo_analog_signal(state)
    fs = float(analog.sampling_rate.rescale(pq.Hz).magnitude)
    values = np.asarray(analog[:, 0].magnitude, dtype=float).ravel()
    sos = signal.butter(3, phase_band, btype="bandpass", fs=fs, output="sos")
    filtered = signal.sosfiltfilt(sos, values)
    filtered_signal = neo.AnalogSignal(
        filtered,
        units=pq.uV,
        sampling_rate=fs * pq.Hz,
        t_start=0 * pq.s,
    )
    analytic = hilbert(filtered_signal)
    analytic_phase = np.angle(np.asarray(analytic.magnitude).ravel())
    duration = len(filtered) / fs
    unit_ids, trains = to_neo_spike_trains(state)
    rng = np.random.default_rng(20260725)
    rows = []
    phase_histograms = {}
    for unit_id, train in zip(unit_ids, trains):
        in_range = train[(train >= 0 * pq.s) & (train < duration * pq.s)]
        phases, _, _ = spike_triggered_phase(analytic, [in_range], interpolate=True)
        phase_values = np.asarray(phases[0], dtype=float)
        preferred_phase, vector_strength = mean_phase_vector(phase_values)
        surrogates = np.zeros(surrogate_count, dtype=float)
        spike_seconds = np.asarray(in_range.rescale(pq.s).magnitude, dtype=float)
        spike_indices = np.clip(
            np.round(spike_seconds * fs).astype(int),
            0,
            len(analytic_phase) - 1,
        )
        for index in range(surrogate_count):
            minimum_shift = max(round(0.5 * fs), 1)
            maximum_shift = max(len(analytic_phase) - minimum_shift, minimum_shift + 1)
            shift = int(rng.integers(minimum_shift, maximum_shift))
            shifted_phases = analytic_phase[
                np.mod(spike_indices + shift, len(analytic_phase))
            ]
            surrogates[index] = float(
                np.abs(np.mean(np.exp(1j * shifted_phases)))
            )
        surrogate_p = float(
            (1 + np.count_nonzero(surrogates >= vector_strength))
            / (surrogate_count + 1)
        )
        counts, edges = np.histogram(
            phase_values, bins=np.linspace(-np.pi, np.pi, 19)
        )
        phase_histograms[int(unit_id)] = {
            "centers": (edges[:-1] + edges[1:]) / 2,
            "counts": counts,
        }
        rows.append(
            {
                "unit_id": int(unit_id),
                "spike_count": len(phase_values),
                "preferred_phase_rad": float(preferred_phase),
                "vector_strength": float(vector_strength),
                "rayleigh_p": _rayleigh_p_value(
                    float(vector_strength), len(phase_values)
                ),
                "surrogate_p": surrogate_p,
            }
        )
    result = {
        "provider": provider_status(),
        "channel_id": int(channels[0]),
        "phase_band_hz": list(phase_band),
        "surrogate_count": int(surrogate_count),
        "rows": rows,
        "phase_histograms": phase_histograms,
        "pac": _phase_amplitude_coupling(values, fs),
    }
    state.spike_field_analysis = result
    state.log(
        "Spike-field analysis completed: phase preference, vector strength, "
        "Rayleigh approximation, circular-shift surrogates, and PAC"
    )
    return result


def _load_respiration_reference(state: ProjectState) -> tuple[np.ndarray, float, list[dict]]:
    path_value = state.metadata.get("respiration_reference")
    path = Path(path_value) if path_value else None
    if path and path.exists():
        values = np.asarray(np.load(path), dtype=float)
        fs = float(state.metadata.get("respiration_sampling_rate_hz", 1_000.0))
        epochs = list(state.metadata.get("behavioral_state_epochs", []))
        return values, fs, epochs
    analog, _ = to_neo_analog_signal(state, channels=[_usable_channels(state, 1)[0]])
    values = np.asarray(analog[:, 0].magnitude, dtype=float).ravel()
    fs = float(analog.sampling_rate.rescale(pq.Hz).magnitude)
    epochs = [
        {
            "state": "recording",
            "start_seconds": 0.0,
            "stop_seconds": len(values) / fs,
        }
    ]
    return values, fs, epochs


def run_respiration_case(state: ProjectState) -> dict:
    respiration, respiration_fs, epochs = _load_respiration_reference(state)
    analog, channels = to_neo_analog_signal(state)
    lfp_fs = float(analog.sampling_rate.rescale(pq.Hz).magnitude)
    lfp = np.asarray(analog[:, 0].magnitude, dtype=float).ravel()
    duration = min(len(respiration) / respiration_fs, len(lfp) / lfp_fs)
    rows = []
    state_curves = {}
    for epoch in epochs:
        name = str(epoch["state"])
        start = max(float(epoch["start_seconds"]), 0.0)
        stop = min(float(epoch["stop_seconds"]), duration)
        respiration_segment = respiration[
            int(start * respiration_fs) : int(stop * respiration_fs)
        ]
        lfp_segment = lfp[int(start * lfp_fs) : int(stop * lfp_fs)]
        if len(respiration_segment) < respiration_fs:
            continue
        frequencies, respiration_psd = signal.welch(
            respiration_segment,
            fs=respiration_fs,
            nperseg=min(int(2 * respiration_fs), len(respiration_segment)),
        )
        breathing_mask = (frequencies >= 1.0) & (frequencies <= 12.0)
        breathing_frequency = float(
            frequencies[breathing_mask][np.argmax(respiration_psd[breathing_mask])]
        )
        coherence_f, coherence = signal.coherence(
            respiration_segment[: min(len(respiration_segment), len(lfp_segment))],
            lfp_segment[: min(len(respiration_segment), len(lfp_segment))],
            fs=min(respiration_fs, lfp_fs),
            nperseg=min(int(respiration_fs), len(respiration_segment)),
        )
        coherence_mask = (coherence_f >= 1.0) & (coherence_f <= 12.0)
        peak_coherence = float(np.max(coherence[coherence_mask]))
        filtered = signal.sosfiltfilt(
            signal.butter(3, (1.0, 12.0), btype="bandpass", fs=respiration_fs, output="sos"),
            respiration_segment,
        )
        troughs, _ = signal.find_peaks(
            -filtered, distance=max(int(respiration_fs / 12.0), 1)
        )
        cycles = np.diff(troughs) / respiration_fs
        cycle_cv = (
            float(np.std(cycles) / np.mean(cycles))
            if cycles.size and np.mean(cycles) > 0
            else float("nan")
        )
        pac = _phase_amplitude_coupling(lfp_segment, lfp_fs)
        rows.append(
            {
                "state": name,
                "duration_seconds": stop - start,
                "respiration_peak_hz": breathing_frequency,
                "cycle_cv": cycle_cv,
                "peak_coherence": peak_coherence,
                "pac_kld": pac["kld"],
            }
        )
        state_curves[name] = {
            "respiration_psd_frequencies_hz": frequencies,
            "respiration_psd": respiration_psd,
            "coherence_frequencies_hz": coherence_f,
            "coherence": coherence,
            "pac": pac,
        }
    result = {
        "label": "Method-inspired validation case on NeuroEphys AI simulated data",
        "paper": SOURCES[-1],
        "respiration_source": (
            "simulated reference"
            if state.metadata.get("respiration_reference")
            else "LFP proxy"
        ),
        "lfp_channel": int(channels[0]),
        "rows": rows,
        "state_curves": state_curves,
        "limitations": [
            "This is not the original paper dataset and does not reproduce its numerical findings.",
            "The case demonstrates the analysis structure and records every parameter.",
            "Scientific conclusions require biological data, experimental metadata, and subject-level statistics.",
        ],
    }
    state.case_studies["respiration"] = result
    state.log(
        "Respiration case completed on NeuroEphys AI data; results are explicitly "
        "separated from the cited paper's findings"
    )
    return result


def run_neural_toolkit(state: ProjectState) -> dict:
    result = {
        "event_aligned": event_aligned_analysis(state),
        "spike_train": run_spike_train_suite(state),
    }
    lfp_available = state.metadata.get("acquisition_preprocessing", {}).get(
        "lfp_available",
        True,
    )
    if state.ready and lfp_available:
        result["lfp"] = run_lfp_suite(state)
        result["spike_field"] = run_spike_field_suite(state)
        result["respiration_case"] = run_respiration_case(state)
    else:
        reason = (
            state.metadata.get("acquisition_preprocessing", {}).get(
                "lfp_unavailable_reason"
            )
            or "raw voltage unavailable"
        )
        result["lfp"] = {"skipped": True, "reason": reason}
        result["spike_field"] = {"skipped": True, "reason": reason}
        result["respiration_case"] = {
            "skipped": True,
            "reason": reason,
        }
    return result
