from __future__ import annotations

import warnings
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
    if method == "holm":
        order = np.argsort(values)
        ranked = values[order] * (len(values) - np.arange(len(values)))
        ranked = np.maximum.accumulate(ranked)
        adjusted = np.empty_like(ranked)
        adjusted[order] = np.minimum(ranked, 1.0)
        return adjusted
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


def independent_effect(first: np.ndarray, second: np.ndarray) -> dict[str, float]:
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    n1, n2 = len(first), len(second)
    variance = (
        (n1 - 1) * np.var(first, ddof=1) + (n2 - 1) * np.var(second, ddof=1)
    ) / max(n1 + n2 - 2, 1)
    pooled = float(np.sqrt(max(variance, 0.0)))
    cohens_d = float((np.mean(second) - np.mean(first)) / pooled) if pooled else 0.0
    correction = 1 - 3 / max(4 * (n1 + n2) - 9, 1)
    return {
        "cohens_d": cohens_d,
        "hedges_g": float(cohens_d * correction),
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
    conditions = np.asarray(state.analysis.get("conditions", []), dtype=str)
    labels, label_counts = np.unique(conditions, return_counts=True)
    usable_labels = [
        label
        for label, _ in sorted(
            zip(labels, label_counts), key=lambda item: item[1], reverse=True
        )
        if label.lower() not in {"unknown", "nan", "none"}
    ][:2]
    mixed_records: list[dict] = []
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
        delta = response - baseline
        shapiro_p = (
            float(stats.shapiro(delta).pvalue)
            if 3 <= len(delta) <= 5000 and not np.allclose(delta, delta[0])
            else 1.0
        )
        pearson_r, pearson_p = stats.pearsonr(np.arange(len(response)), response)
        spearman_r, spearman_p = stats.spearmanr(np.arange(len(response)), response)
        condition_results = {
            "condition_welch_t": np.nan,
            "condition_welch_p": np.nan,
            "condition_mannwhitney_u": np.nan,
            "condition_mannwhitney_p": np.nan,
            "condition_levene_p": np.nan,
            "condition_anova_p": np.nan,
            "condition_kruskal_p": np.nan,
            "condition_hedges_g": np.nan,
        }
        if len(usable_labels) == 2 and len(conditions) == len(response):
            first = response[conditions == usable_labels[0]]
            second = response[conditions == usable_labels[1]]
            if len(first) >= 2 and len(second) >= 2:
                welch = stats.ttest_ind(second, first, equal_var=False)
                mannwhitney = stats.mannwhitneyu(second, first, alternative="two-sided")
                levene = stats.levene(first, second, center="median")
                anova = stats.f_oneway(first, second)
                kruskal = stats.kruskal(first, second)
                independent = independent_effect(first, second)
                condition_results = {
                    "condition_welch_t": float(welch.statistic),
                    "condition_welch_p": float(welch.pvalue),
                    "condition_mannwhitney_u": float(mannwhitney.statistic),
                    "condition_mannwhitney_p": float(mannwhitney.pvalue),
                    "condition_levene_p": float(levene.pvalue),
                    "condition_anova_p": float(anova.pvalue),
                    "condition_kruskal_p": float(kruskal.pvalue),
                    "condition_hedges_g": independent["hedges_g"],
                }
        for trial_index, value in enumerate(delta):
            mixed_records.append(
                {
                    "unit": str(unit_id),
                    "trial": trial_index,
                    "delta": float(value),
                    "condition": (
                        str(conditions[trial_index])
                        if trial_index < len(conditions)
                        else "all"
                    ),
                }
            )
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
                "shapiro_p": shapiro_p,
                "pearson_trial_r": float(pearson_r),
                "pearson_trial_p": float(pearson_p),
                "spearman_trial_r": float(spearman_r),
                "spearman_trial_p": float(spearman_p),
                "ci95_low_hz": ci_low,
                "ci95_high_hz": ci_high,
                **condition_results,
            }
        )
    raw_p = np.asarray([row["permutation_p"] for row in rows])
    fdr = adjust_pvalues(raw_p, "fdr_bh")
    bonferroni = adjust_pvalues(raw_p, "bonferroni")
    holm = adjust_pvalues(raw_p, "holm")
    for row, q_value, corrected, holm_value in zip(rows, fdr, bonferroni, holm):
        row["fdr_q"] = float(q_value)
        row["bonferroni_p"] = float(corrected)
        row["holm_p"] = float(holm_value)
        row["significant_fdr"] = bool(q_value < 0.05)
    mixed_effects = {
        "available": False,
        "formula": "delta ~ C(condition), random intercept by unit",
    }
    if len(usable_labels) == 2 and mixed_records:
        try:
            import pandas as pd
            import statsmodels.formula.api as smf

            frame = pd.DataFrame(mixed_records)
            frame = frame[frame["condition"].isin(usable_labels)]
            with warnings.catch_warnings(record=True) as model_warnings:
                warnings.simplefilter("always")
                model = smf.mixedlm(
                    "delta ~ C(condition)",
                    frame,
                    groups=frame["unit"],
                ).fit(reml=False, method="lbfgs", disp=False)
            term = next(
                (
                    name
                    for name in model.params.index
                    if name.startswith("C(condition)")
                ),
                None,
            )
            mixed_effects = {
                "available": True,
                "formula": "delta ~ C(condition), random intercept by unit",
                "coefficient": float(model.params[term]) if term else np.nan,
                "p_value": float(model.pvalues[term]) if term else np.nan,
                "converged": bool(model.converged),
                "n_observations": int(model.nobs),
                "groups": int(frame["unit"].nunique()),
                "warnings": [str(item.message) for item in model_warnings],
            }
        except Exception as exc:  # noqa: BLE001 - model is optional evidence
            mixed_effects["error"] = f"{type(exc).__name__}: {exc}"
    result = {
        "rows": rows,
        "primary_test": "paired sign-flip permutation",
        "multiple_comparison": "Benjamini-Hochberg FDR",
        "alpha": 0.05,
        "condition_labels": usable_labels,
        "mixed_effects": mixed_effects,
        "significant_count": sum(row["significant_fdr"] for row in rows),
        "available_tests": [
            "paired t-test",
            "Wilcoxon signed-rank",
            "paired permutation",
            "bootstrap confidence interval",
            "Shapiro-Wilk normality check",
            "Welch independent t-test",
            "Mann-Whitney U",
            "Levene variance test",
            "one-way ANOVA",
            "Kruskal-Wallis",
            "Pearson correlation",
            "Spearman correlation",
            "mixed-effects model",
            "Benjamini-Hochberg FDR",
            "Holm",
            "Bonferroni",
        ],
    }
    state.statistics = result
    state.log(
        f"Statistical suite completed: {result['significant_count']}/{len(rows)} "
        "units passed FDR correction"
    )
    return result
