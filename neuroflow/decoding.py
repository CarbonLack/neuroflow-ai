from __future__ import annotations

import numpy as np
from sklearn.base import clone
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_predict,
    cross_val_score,
    permutation_test_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .models import ProjectState

MODELS = {
    "Logistic regression": Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    ),
    "Linear SVM": Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", SVC(kernel="linear", probability=True, class_weight="balanced")),
        ]
    ),
    "Random forest": RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=20260725,
        min_samples_leaf=2,
    ),
}


def trial_feature_matrix(
    state: ProjectState,
    window: tuple[float, float] = (0.0, 0.5),
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    if not state.analysis:
        raise RuntimeError("请先运行事件对齐分析")
    centers = np.asarray(state.analysis["bin_centers"])
    mask = (centers >= window[0]) & (centers < window[1])
    unit_ids = list(state.analysis["units"])
    x = np.column_stack(
        [
            np.asarray(state.analysis["units"][unit]["rates"])[:, mask].mean(axis=1)
            for unit in unit_ids
        ]
    )
    labels = np.asarray(state.analysis["conditions"]).astype(str)
    unique, counts = np.unique(labels, return_counts=True)
    candidates = [
        (label, count)
        for label, count in zip(unique, counts)
        if count >= 2 and label.lower() not in {"unknown", "nan", "none"}
    ]
    candidates.sort(key=lambda item: item[1], reverse=True)
    usable = np.asarray([label for label, _ in candidates[:2]])
    valid = np.isin(labels, usable)
    return x[valid], labels[valid], unit_ids


def _time_resolved_decoding(
    state: ProjectState,
    labels: np.ndarray,
    valid_mask: np.ndarray,
    model,
    cv,
) -> np.ndarray:
    unit_ids = list(state.analysis["units"])
    rates = np.stack(
        [np.asarray(state.analysis["units"][unit]["rates"]) for unit in unit_ids],
        axis=2,
    )
    rates = rates[valid_mask]
    scores = np.zeros(rates.shape[1], dtype=float)
    for bin_index in range(rates.shape[1]):
        scores[bin_index] = cross_val_score(
            clone(model),
            rates[:, bin_index, :],
            labels,
            scoring="balanced_accuracy",
            cv=cv,
            n_jobs=1,
        ).mean()
    return scores


def _population_trajectory(
    state: ProjectState,
    labels: np.ndarray,
    valid_mask: np.ndarray,
    classes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    unit_ids = list(state.analysis["units"])
    rates = np.stack(
        [np.asarray(state.analysis["units"][unit]["rates"]) for unit in unit_ids],
        axis=2,
    )[valid_mask]
    condition_means = np.stack([rates[labels == label].mean(axis=0) for label in classes])
    bins = condition_means.shape[1]
    flattened = condition_means.reshape(-1, condition_means.shape[-1])
    components = min(3, flattened.shape[0], flattened.shape[1])
    transformed = PCA(n_components=components).fit_transform(
        StandardScaler().fit_transform(flattened)
    )
    trajectories = transformed.reshape(len(classes), bins, components)
    distance = np.linalg.norm(trajectories[0] - trajectories[1], axis=1)
    return trajectories, distance


def run_decoding_suite(
    state: ProjectState,
    model_name: str = "Logistic regression",
    n_splits: int = 5,
    n_permutations: int = 200,
) -> dict:
    x, labels, unit_ids = trial_feature_matrix(state)
    all_labels = np.asarray(state.analysis["conditions"]).astype(str)
    valid_mask = np.isin(all_labels, np.unique(labels))
    classes, counts = np.unique(labels, return_counts=True)
    if len(classes) != 2:
        raise ValueError("当前演示解码器需要恰好两个条件")
    folds = min(n_splits, int(counts.min()))
    if folds < 2:
        raise ValueError("每个条件至少需要两个 trial")
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=20260725)
    model = clone(MODELS[model_name])
    predictions = cross_val_predict(model, x, labels, cv=cv, method="predict")
    probabilities = cross_val_predict(
        model, x, labels, cv=cv, method="predict_proba"
    )[:, 1]
    binary = (labels == classes[1]).astype(int)
    score = balanced_accuracy_score(labels, predictions)
    auc = roc_auc_score(binary, probabilities)
    permutation_score, null_scores, p_value = permutation_test_score(
        model,
        x,
        labels,
        scoring="balanced_accuracy",
        cv=cv,
        n_permutations=n_permutations,
        random_state=20260725,
        n_jobs=1,
    )
    fitted = clone(model).fit(x, labels)
    if model_name == "Random forest":
        importance = fitted.feature_importances_
    else:
        importance = np.abs(fitted.named_steps["model"].coef_[0])
    pca_components = min(3, x.shape[0], x.shape[1])
    trajectory = PCA(n_components=pca_components).fit_transform(
        StandardScaler().fit_transform(x)
    )
    time_scores = _time_resolved_decoding(state, labels, valid_mask, model, cv)
    population_trajectories, trajectory_distance = _population_trajectory(
        state, labels, valid_mask, classes
    )
    result = {
        "model": model_name,
        "classes": classes.tolist(),
        "n_trials": len(labels),
        "n_features": int(x.shape[1]),
        "cv_folds": folds,
        "balanced_accuracy": float(score),
        "roc_auc": float(auc),
        "permutation_score": float(permutation_score),
        "permutation_p": float(p_value),
        "null_scores": null_scores,
        "confusion_matrix": confusion_matrix(labels, predictions, labels=classes),
        "predictions": predictions,
        "labels": labels,
        "probabilities": probabilities,
        "feature_importance": np.asarray(importance),
        "unit_ids": unit_ids,
        "pca": trajectory,
        "bin_centers": np.asarray(state.analysis["bin_centers"]),
        "time_resolved_accuracy": time_scores,
        "population_trajectories": population_trajectories,
        "trajectory_distance": trajectory_distance,
        "leakage_checks": [
            "标准化仅在交叉验证训练折内拟合",
            "特征为 trial 级窗口放电率",
            "标签未进入特征构建",
        ],
    }
    state.decoding = result
    state.log(
        f"{model_name} 解码完成：balanced accuracy={score:.3f}，"
        f"permutation p={p_value:.4f}"
    )
    return result
