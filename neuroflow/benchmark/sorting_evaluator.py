from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


def _load_npz(path: Path) -> dict[int, np.ndarray]:
    with np.load(path) as archive:
        return {int(key.rsplit("_", 1)[-1]): np.asarray(archive[key], dtype=float) for key in archive.files}


def _load_candidate(path: Path, sampling_rate: float) -> dict[int, np.ndarray]:
    times = np.load(path / "spike_times.npy").reshape(-1).astype(float) / sampling_rate
    clusters = np.load(path / "spike_clusters.npy").reshape(-1).astype(int)
    return {int(cluster): times[clusters == cluster] for cluster in np.unique(clusters)}


def _matches(left: np.ndarray, right: np.ndarray, tolerance: float) -> int:
    if not len(left) or not len(right):
        return 0
    # Vectorized nearest-neighbour assignment.  Unique candidate indices enforce
    # the one-spike/one-match rule while avoiding Python loops over millions of
    # spikes in the 20-minute sessions.
    positions = np.searchsorted(right, left)
    high = np.clip(positions, 0, len(right) - 1)
    low = np.clip(positions - 1, 0, len(right) - 1)
    use_low = np.abs(left - right[low]) <= np.abs(left - right[high])
    nearest = np.where(use_low, low, high)
    valid = np.abs(left - right[nearest]) <= tolerance
    return int(len(np.unique(nearest[valid])))


def evaluate_candidate_sorting(
    truth_archive: Path,
    candidate_root: Path,
    sampling_rate: float,
    tolerance_seconds: float = 0.0004,
) -> dict:
    truth = _load_npz(truth_archive)
    candidate = _load_candidate(candidate_root, sampling_rate)
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
        "这些候选结果故意包含合并、拆分、漏检和误检，用于测试 Unit QC 与 sorter 比较，不是“完美答案”。", "",
    ]
    (output / "sorting_ground_truth_comparison.md").write_text("\n".join(lines), encoding="utf-8")
