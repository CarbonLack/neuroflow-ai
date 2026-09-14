from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def export_blinded_candidate_sorting(
    root: Path,
    rng: np.random.Generator,
    spikes: dict[int, np.ndarray],
    sampling_rate: float,
    duration_seconds: float,
) -> dict:
    """Create a deliberately imperfect Kilosort/Phy-compatible challenge result.

    This result is safe to expose to the App.  Its construction recipe stays in
    ground truth, while the exported folder contains only candidate spike times
    and cluster labels.
    """
    root.mkdir(parents=True, exist_ok=True)
    unit_ids = sorted(spikes)
    candidate: dict[int, np.ndarray] = {}
    recipe: list[dict] = []
    next_cluster = 0
    index = 0
    while index < len(unit_ids):
        unit_id = unit_ids[index]
        values = spikes[unit_id]
        if index + 1 < len(unit_ids) and index % 17 == 0:
            other = unit_ids[index + 1]
            merged = np.sort(np.r_[values, spikes[other]])
            candidate[next_cluster] = merged
            recipe.append({"candidate_cluster": next_cluster, "operation": "merge", "true_units": [unit_id, other]})
            index += 2
        elif index % 13 == 0 and len(values) > 20:
            split_mask = rng.random(len(values)) < 0.52
            candidate[next_cluster] = values[split_mask]
            candidate[next_cluster + 1] = values[~split_mask]
            recipe.extend([
                {"candidate_cluster": next_cluster, "operation": "split_a", "true_units": [unit_id]},
                {"candidate_cluster": next_cluster + 1, "operation": "split_b", "true_units": [unit_id]},
            ])
            next_cluster += 1
            index += 1
        else:
            detection = 0.70 if index % 11 == 0 else float(rng.uniform(0.86, 0.98))
            kept = values[rng.random(len(values)) < detection]
            jitter = rng.normal(0, 0.000045 if index % 9 else 0.00011, len(kept))
            kept = np.clip(kept + jitter, 0, duration_seconds - 1 / sampling_rate)
            false_count = int(len(kept) * (0.018 if index % 10 else 0.075))
            false = rng.uniform(0.05, duration_seconds - 0.05, false_count)
            candidate[next_cluster] = np.sort(np.r_[kept, false])
            recipe.append({
                "candidate_cluster": next_cluster,
                "operation": "detect_with_errors",
                "true_units": [unit_id],
                "target_detection_fraction": detection,
                "false_positive_count": false_count,
            })
            index += 1
        next_cluster += 1

    all_times: list[np.ndarray] = []
    all_clusters: list[np.ndarray] = []
    for cluster, values in candidate.items():
        samples = np.rint(values * sampling_rate).astype(np.int64)
        all_times.append(samples)
        all_clusters.append(np.full(len(samples), cluster, dtype=np.int32))
    times = np.concatenate(all_times) if all_times else np.empty(0, dtype=np.int64)
    clusters = np.concatenate(all_clusters) if all_clusters else np.empty(0, dtype=np.int32)
    order = np.argsort(times, kind="stable")
    np.save(root / "spike_times.npy", times[order, None])
    np.save(root / "spike_clusters.npy", clusters[order, None])
    (root / "README.txt").write_text(
        "这是故意包含漏检、误检、合并和拆分的盲测 sorting 结果。\n"
        "可在 NeuroEphys AI 中选择‘已有 sorting 结果’导入本文件夹；请勿将它当作标准答案。\n",
        encoding="utf-8",
    )
    summary = {"cluster_count": len(candidate), "spike_count": int(len(times)), "recipe": recipe}
    return summary


def write_private_recipe(root: Path, summary: dict) -> None:
    (root / "candidate_sorting_recipe.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
