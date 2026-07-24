from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy import stats

from .models import ProjectState


def adjust_pvalues(p_values: np.ndarray, method: str = "fdr_bh") -> np.ndarray:
    values = np.asarray(p_values, dtype=float)
    if values.size == 0:
        return values
    if method == "bonferroni":
        return np.minimum(values * len(values), 1.0)
    if method != "fdr_bh":
        return values.copy()
    order = np.argsort(values)
    ranked = values[order] * len(values) / np.arange(1, len(values) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty_like(ranked)
    adjusted[order] = np.minimum(ranked, 1.0)
    return adjusted


def paired_effect(before: np.ndarray, after: np.ndarray) -> dict[str, float]:
    delta = np.asarray(after, float) - np.asarray(before, float)
    sd = float(np.std(delta, ddof=1)) if delta.size > 1 else 0.0
    dz = float(np.mean(delta) / sd) if sd > 0 else 0.0
    positive = np.count_nonzero(delta > 0)
    negative = np.count_nonzero(delta < 0)
    rank_biserial = (positive - negative) / max(positive + negative, 1)
    return {
        "mean_difference": float(np.mean(delta)),
        "median_difference": float(np.median(delta)),
        "cohens_dz": dz,
        "rank_biserial": float(rank_biserial),
    }


def bootstrap_ci(
    values: np.ndarray,
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_resamples: int = 2000,
    seed: int = 20260725,
) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if values.size < 2:
        value = float(statistic(values)) if values.size else 0.0
        return value, value
    result = stats.bootstrap(
        (values,),
        statistic,
        confidence_level=0.95,
        n_resamples=n_resamples,
        random_state=np.random.default_rng(seed),
        method="percentile",
    )
    return float(result.confidence_interval.low), float(result.confidence_interval.high)


def permutation_paired(
    before: np.ndarray,
    after: np.ndarray,
    n_permutations: int = 5000,
    seed: int = 20260725,
) -> float:
    delta = np.asarray(after, float) - np.asarray(before, float)
    observed = abs(float(np.mean(delta)))
    rng = np.random.default_rng(seed)
    signs = rng.choice((-1.0, 1.0), size=(n_permutations, len(delta)))
    null = np.abs((signs * delta).mean(axis=1))
    return float((np.count_nonzero(null >= observed) + 1) / (n_permutations + 1))


def run_statistical_suite(state: ProjectState) -> dict:
    if not state.analysis:
        raise RuntimeError("请先运行事件对齐分析")
    rows = []
    for unit_id, unit in state.analysis["units"].items():
        centers = np.asarray(state.analysis["bin_centers"])
        rates = np.asarray(unit["rates"])
        baseline = rates[:, (centers >= -0.5) & (centers < 0.0)].mean(axis=1)
        response = rates[:, (centers >= 0.0) & (centers < 0.5)].mean(axis=1)
        if np.allclose(baseline, response):
            t_value = w_value = 0.0
            t_p = w_p = permutation_p = 1.0
        else:
            t_value, t_p = stats.ttest_rel(response, baseline)
            w_value, w_p = stats.wilcoxon(response, baseline)
            permutation_p = permutation_paired(baseline, response)
        effect = paired_effect(baseline, response)
        ci_low, ci_high = bootstrap_ci(response - baseline)
        rows.append(
            {
                "unit_id": int(unit_id),
                "n_trials": len(baseline),
                "paired_t": float(t_value),
                "paired_t_p": float(t_p),
                "wilcoxon_w": float(w_value),
                "wilcoxon_p": float(w_p),
                "permutation_p": permutation_p,
                "effect_hz": effect["mean_difference"],
                "cohens_dz": effect["cohens_dz"],
                "rank_biserial": effect["rank_biserial"],
                "ci95_low_hz": ci_low,
                "ci95_high_hz": ci_high,
            }
        )
    raw_p = np.asarray([row["permutation_p"] for row in rows])
    fdr = adjust_pvalues(raw_p, "fdr_bh")
    bonferroni = adjust_pvalues(raw_p, "bonferroni")
    for row, q_value, corrected in zip(rows, fdr, bonferroni):
        row["fdr_q"] = float(q_value)
        row["bonferroni_p"] = float(corrected)
        row["significant_fdr"] = bool(q_value < 0.05)
    result = {
        "rows": rows,
        "primary_test": "paired sign-flip permutation",
        "multiple_comparison": "Benjamini-Hochberg FDR",
        "alpha": 0.05,
        "significant_count": sum(row["significant_fdr"] for row in rows),
        "available_tests": [
            "paired t-test",
            "Wilcoxon signed-rank",
            "paired permutation",
            "bootstrap confidence interval",
            "Benjamini-Hochberg FDR",
            "Bonferroni",
        ],
    }
    state.statistics = result
    state.log(
        f"统计套件完成：{result['significant_count']}/{len(rows)} units 通过 FDR"
    )
    return result
