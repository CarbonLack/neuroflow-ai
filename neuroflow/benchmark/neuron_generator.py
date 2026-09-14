from __future__ import annotations

import numpy as np


PHENOTYPES = ("regular-spiking-like", "bursting", "low-firing", "high-firing", "fast-spiking-like")


def _class_counts(total: int, proportions: dict[str, float]) -> list[str]:
    keys = list(proportions)
    raw = np.asarray([proportions[key] for key in keys], dtype=float) * total
    counts = np.floor(raw).astype(int)
    for index in np.argsort(raw - counts)[::-1][: total - int(counts.sum())]:
        counts[index] += 1
    return [key for key, count in zip(keys, counts, strict=True) for _ in range(int(count))]


def generate_units(
    rng: np.random.Generator,
    electrode: str,
    channel_count: int,
    count_ranges: dict[str, list[int]],
    proportions: dict[str, dict[str, float]],
) -> list[dict]:
    units: list[dict] = []
    unit_id = 0
    for region_index, region in enumerate(("M1", "mPFC")):
        lo, hi = count_ranges[region]
        total = int(rng.integers(lo, hi + 1))
        classes = _class_counts(total, proportions[region])
        rng.shuffle(classes)
        region_start = region_index * channel_count // 2
        region_stop = (region_index + 1) * channel_count // 2
        for neuron_class in classes:
            phenotype = str(rng.choice(PHENOTYPES, p=[0.38, 0.18, 0.16, 0.18, 0.10]))
            if phenotype == "low-firing":
                baseline = float(np.exp(rng.uniform(np.log(0.5), np.log(2.0))))
            elif phenotype == "fast-spiking-like":
                baseline = float(rng.uniform(20.0, 38.0))
            elif phenotype == "high-firing":
                baseline = float(rng.uniform(10.0, 25.0))
            else:
                baseline = float(np.exp(rng.uniform(np.log(2.0), np.log(14.0))))
            if electrode == "tetrode":
                groups = np.arange(region_start // 4, region_stop // 4)
                group = int(rng.choice(groups))
                peak_channel = group * 4 + int(rng.integers(0, 4))
                electrode_id = f"T{group + 1:02d}"
            else:
                peak_channel = int(rng.integers(region_start + 3, max(region_start + 4, region_stop - 3)))
                electrode_id = "Probe_A" if region == "M1" else "Probe_B"
            lever_type = "none"
            reward_type = "none"
            if neuron_class in {"lever", "mixed"}:
                lever_type = str(rng.choice(["excited", "suppressed"], p=[0.75, 0.25]))
            if neuron_class == "reward_anticipation":
                reward_type = "anticipatory_excited"
            elif neuron_class in {"reward_delivery", "mixed"}:
                reward_type = str(rng.choice(["delivery_excited", "delivery_suppressed"], p=[0.72, 0.28]))
            units.append({
                "unit_id": unit_id, "brain_region": region, "electrode_id": electrode_id,
                "electrode_type": electrode, "peak_channel": peak_channel,
                "estimated_depth_um": float((peak_channel - region_start) * (10 if electrode == "neuropixels" else 62.5)),
                "true_neuron_class": neuron_class, "firing_phenotype": phenotype,
                "baseline_firing_rate_hz": baseline, "lever_modulation_type": lever_type,
                "reward_modulation_type": reward_type,
                "reward_anticipation_onset_sec": float(rng.uniform(-1.25, -0.75)) if "anticipatory" in reward_type else None,
                "response_latency_sec": float(rng.uniform(0.04, 0.18)),
                "response_duration_sec": float(rng.uniform(0.22, 0.85)),
                "response_gain": float(rng.uniform(1.5, 4.0)),
                "baseline_drift_fraction": float(rng.uniform(-0.16, 0.16)),
                "amplitude_drift_fraction": float(rng.uniform(-0.14, 0.14)),
                "spatial_drift_sites": int(rng.integers(-3, 4)) if electrode == "neuropixels" else 0,
                "relative_wire_drift_fraction": float(rng.uniform(-0.12, 0.12)) if electrode == "tetrode" else 0.0,
                "sorting_difficulty": str(rng.choice(["typical", "similar_waveform", "low_snr", "partial_overlap", "burst_shape_change"], p=[0.58, 0.12, 0.12, 0.10, 0.08])),
            })
            unit_id += 1
    return units
