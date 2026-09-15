from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from numba import njit


def _load_npz(path: Path) -> dict[int, np.ndarray]:
    with np.load(path) as archive:
        return {int(key.rsplit("_", 1)[-1]): np.asarray(archive[key], dtype=float) for key in archive.files}


def _load_candidate(path: Path, sampling_rate: float) -> dict[int, np.ndarray]:
    times = np.load(path / "spike_times.npy").reshape(-1).astype(float) / sampling_rate
    clusters = np.load(path / "spike_clusters.npy").reshape(-1).astype(int)
    return {int(cluster): times[clusters == cluster] for cluster in np.unique(clusters)}


@njit(cache=True)
def _matches(left: np.ndarray, right: np.ndarray, tolerance: float) -> int:
    # Sorted two-pointer matching maximizes the number of one-to-one matches.
    i = j = count = 0
    while i < len(left) and j < len(right):
        delta = right[j] - left[i]
        if abs(delta) <= tolerance:
            count += 1
            i += 1
            j += 1
        elif delta < -tolerance:
            j += 1
        else:
            i += 1
    return count


def evaluate_candidate_sorting(
    truth_archive: Path,
    candidate_root: Path,
    sampling_rate: float,
    tolerance_seconds: float = 0.0004,
) -> dict:
    truth = _load_npz(truth_archive)
    candidate = _load_candidate(candidate_root, sampling_rate)
    truth = {key: np.sort(value) for key, value in truth.items()}
    candidate = {key: np.sort(value) for key, value in candidate.items()}
    truth_ids, candidate_ids = sorted(truth), sorted(candidate)
    score = np.zeros((len(truth_ids), len(candidate_ids)), dtype=float)
    matches = np.zeros_like(score, dtype=int)
    for row, true_id in enumerate(truth_ids):
        for column, candidate_id in enumerate(candidate_ids):
            match = _matches(truth[true_id], candidate[candidate_id], tolerance_seconds)
            matches[row, column] = match
            score[row, column] = match / max(len(truth[true_id]) + len(candidate[candidate_id]) - match, 1)
    rows, columns = linear_sum_assignment(-score) if score.size else (np.array([], dtype=int), np.array([], dtype=int))
    pairs = []
    for row, column in zip(rows, columns, strict=True):
        true_id, candidate_id = truth_ids[row], candidate_ids[column]
        match = int(matches[row, column])
        recall = match / max(len(truth[true_id]), 1)
        precision = match / max(len(candidate[candidate_id]), 1)
        pairs.append({
            "true_unit": true_id, "candidate_cluster": candidate_id, "matching_spikes": match,
            "recall": recall, "precision": precision,
            "f1": 2 * recall * precision / max(recall + precision, 1e-12),
            "jaccard": float(score[row, column]),
        })
    return {
        "tolerance_seconds": tolerance_seconds,
        "true_unit_count": len(truth),
        "candidate_cluster_count": len(candidate),
        "matched_pairs": pairs,
        "unassigned_true_units": sorted(set(truth_ids) - {p['true_unit'] for p in pairs}),
        "unassigned_candidate_clusters": sorted(set(candidate_ids) - {p['candidate_cluster'] for p in pairs}),
        "mean_recall_all_true_units": float(sum(p['recall'] for p in pairs) / max(len(truth_ids), 1)),
        "well_recovered_f1_ge_0_8": sum(p['f1'] >= 0.8 for p in pairs),
        "median_scope": "Assigned pairs only; see all-unit recall and unassigned units.",
        "median_recall": float(np.median([row["recall"] for row in pairs])) if pairs else 0.0,
        "median_precision": float(np.median([row["precision"] for row in pairs])) if pairs else 0.0,
        "median_f1": float(np.median([row["f1"] for row in pairs])) if pairs else 0.0,
    }


def write_sorting_evaluation(result: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "sorting_ground_truth_comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 盲测 sorting 与 ground truth 对照", "",
        f"- 匹配容差：{result['tolerance_seconds'] * 1000:.2f} ms",
        f"- 真实 Unit：{result['true_unit_count']}",
        f"- 候选簇：{result['candidate_cluster_count']}",
        f"- 中位 Recall：{result['median_recall']:.3f}",
        f"- 中位 Precision：{result['median_precision']:.3f}",
        f"- 中位 F1：{result['median_f1']:.3f}", "",
        "中位数只覆盖配对的簇，不代表全部真实神经元。未配对单元、全体真实单元平均召回率见 JSON；候选簇不等于已通过人工复核的单细胞。", "",
    ]
    (output / "sorting_ground_truth_comparison.md").write_text("\n".join(lines), encoding="utf-8")
