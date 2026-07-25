from __future__ import annotations

import numpy as np
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge
from sklearn.metrics import (
    adjusted_rand_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_predict,
    cross_val_score,
    permutation_test_score,
)
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, SVR

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
    "RBF SVM": Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", SVC(kernel="rbf", probability=True, class_weight="balanced")),
        ]
    ),
    "Random forest": RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=20260725,
        min_samples_leaf=2,
    ),
    "Extra trees": ExtraTreesClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=20260725,
        min_samples_leaf=2,
    ),
    "Gradient boosting": GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=2,
        random_state=20260725,
    ),
    "k-nearest neighbors": Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", KNeighborsClassifier(n_neighbors=5, weights="distance")),
        ]
    ),
    "Linear discriminant analysis": Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", LinearDiscriminantAnalysis(shrinkage="auto", solver="lsqr")),
        ]
    ),
    "Gaussian naive Bayes": Pipeline(
        [("scale", StandardScaler()), ("model", GaussianNB())]
    ),
    "Multilayer perceptron": Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                MLPClassifier(
                    hidden_layer_sizes=(32, 16),
                    max_iter=800,
                    early_stopping=False,
                    random_state=20260725,
                ),
            ),
        ]
    ),
}

MODEL_DESCRIPTIONS = {
    "Logistic regression": "Interpretable linear baseline with L2 regularization.",
    "Linear SVM": "Linear maximum-margin classifier for high-dimensional features.",
    "RBF SVM": "Nonlinear kernel classifier; sensitive to scaling and sample size.",
    "Random forest": "Bagged decision trees with nonlinear interactions and importance.",
    "Extra trees": "Highly randomized tree ensemble; fast nonlinear comparison.",
    "Gradient boosting": "Sequentially boosted trees for structured nonlinear effects.",
    "k-nearest neighbors": "Local distance-based classifier; useful as a simple nonlinear baseline.",
    "Linear discriminant analysis": "Linear class separation with shrinkage covariance.",
    "Gaussian naive Bayes": "Fast probabilistic baseline with conditional-independence assumptions.",
    "Multilayer perceptron": "Small neural network; needs more trials and careful validation.",
    "XGBoost": "Regularized gradient-boosted trees with feature subsampling.",
}

REGRESSION_MODELS = {
    "Ridge regression": Pipeline(
        [("scale", StandardScaler()), ("model", Ridge(alpha=1.0))]
    ),
    "Elastic net": Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                ElasticNet(
                    alpha=0.05,
                    l1_ratio=0.3,
                    max_iter=5000,
                    random_state=20260725,
                ),
            ),
        ]
    ),
    "Support vector regression": Pipeline(
        [("scale", StandardScaler()), ("model", SVR(kernel="rbf", C=1.0))]
    ),
    "Random forest regression": RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        random_state=20260725,
        n_jobs=1,
    ),
    "Gradient boosting regression": GradientBoostingRegressor(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=2,
        random_state=20260725,
    ),
}

REGRESSION_DESCRIPTIONS = {
    "Ridge regression": "Regularized linear prediction of a continuous trial variable.",
    "Elastic net": "Sparse linear model combining L1 and L2 penalties.",
    "Support vector regression": "Nonlinear RBF-kernel regression.",
    "Random forest regression": "Bagged nonlinear trees for continuous targets.",
    "Gradient boosting regression": "Boosted trees optimized for continuous targets.",
}

MODELS["XGBoost"] = None


def _model_instance(model_name: str):
    if model_name != "XGBoost":
        return clone(MODELS[model_name])
    try:
        from xgboost import XGBClassifier
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "XGBoost is not available in this installation. "
            "Choose another classifier or repair the optional XGBoost component."
        ) from exc
    return XGBClassifier(
        n_estimators=180,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        eval_metric="logloss",
        n_jobs=1,
        random_state=20260725,
    )


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
    condition_means = np.stack(
        [rates[labels == label].mean(axis=0) for label in classes]
    )
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
    model = _model_instance(model_name)
    label_lookup = {label: index for index, label in enumerate(classes)}
    model_labels = np.asarray([label_lookup[label] for label in labels])
    predictions_model = cross_val_predict(
        model, x, model_labels, cv=cv, method="predict"
    )
    probabilities = cross_val_predict(
        model, x, model_labels, cv=cv, method="predict_proba"
    )[:, 1]
    predictions = classes[np.asarray(predictions_model, dtype=int)]
    binary = (labels == classes[1]).astype(int)
    score = balanced_accuracy_score(labels, predictions)
    auc = roc_auc_score(binary, probabilities)
    permutation_score, null_scores, p_value = permutation_test_score(
        model,
        x,
        model_labels,
        scoring="balanced_accuracy",
        cv=cv,
        n_permutations=n_permutations,
        random_state=20260725,
        n_jobs=1,
    )
    fitted = clone(model).fit(x, model_labels)
    if hasattr(fitted, "feature_importances_"):
        importance = fitted.feature_importances_
    elif hasattr(fitted, "named_steps") and hasattr(
        fitted.named_steps["model"], "coef_"
    ):
        importance = np.abs(fitted.named_steps["model"].coef_[0])
    else:
        importance = permutation_importance(
            fitted,
            x,
            model_labels,
            scoring="balanced_accuracy",
            n_repeats=8,
            random_state=20260725,
            n_jobs=1,
        ).importances_mean
    pca_components = min(3, x.shape[0], x.shape[1])
    trajectory = PCA(n_components=pca_components).fit_transform(
        StandardScaler().fit_transform(x)
    )
    time_scores = _time_resolved_decoding(state, model_labels, valid_mask, model, cv)
    population_trajectories, trajectory_distance = _population_trajectory(
        state, labels, valid_mask, classes
    )
    fpr, tpr, thresholds = roc_curve(binary, probabilities)
    scaled = StandardScaler().fit_transform(x)
    kmeans_labels = KMeans(n_clusters=2, n_init=20, random_state=20260725).fit_predict(
        scaled
    )
    gmm_labels = GaussianMixture(
        n_components=2, covariance_type="full", random_state=20260725
    ).fit_predict(scaled)
    cluster_results = {
        "kmeans_silhouette": float(silhouette_score(scaled, kmeans_labels)),
        "kmeans_adjusted_rand": float(adjusted_rand_score(binary, kmeans_labels)),
        "gmm_silhouette": float(silhouette_score(scaled, gmm_labels)),
        "gmm_adjusted_rand": float(adjusted_rand_score(binary, gmm_labels)),
    }
    result = {
        "model": model_name,
        "classes": classes.tolist(),
        "n_trials": len(labels),
        "n_features": int(x.shape[1]),
        "cv_folds": folds,
        "balanced_accuracy": float(score),
        "roc_auc": float(auc),
        "precision": float(
            precision_score(labels, predictions, pos_label=classes[1], zero_division=0)
        ),
        "recall": float(
            recall_score(labels, predictions, pos_label=classes[1], zero_division=0)
        ),
        "f1": float(
            f1_score(labels, predictions, pos_label=classes[1], zero_division=0)
        ),
        "roc_curve": {
            "fpr": fpr,
            "tpr": tpr,
            "thresholds": thresholds,
        },
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
        "cluster_results": cluster_results,
        "available_models": list(MODELS),
        "available_unsupervised_methods": [
            "PCA",
            "K-means",
            "Gaussian mixture model",
        ],
        "leakage_checks": [
            "标准化仅在交叉验证训练折内拟合",
            "特征为 trial 级窗口放电率",
            "标签未进入特征构建",
        ],
    }
    state.decoding = result
    state.log(
        f"{model_name} decoding completed: balanced accuracy={score:.3f}, "
        f"permutation p={p_value:.4f}"
    )
    return result


def _reaction_time_target(state: ProjectState) -> np.ndarray:
    records = state.trials if len(state.trials) == len(state.events) else state.events
    values = []
    for record in records:
        if record.get("reaction_time") is not None:
            values.append(float(record["reaction_time"]))
            continue
        movement = record.get("firstMovement_times")
        stimulus = record.get("stimOn_times", record.get("time_seconds"))
        try:
            values.append(float(movement) - float(stimulus))
        except (TypeError, ValueError):
            values.append(np.nan)
    return np.asarray(values, dtype=float)


def run_regression_suite(
    state: ProjectState,
    model_name: str = "Ridge regression",
    n_splits: int = 5,
) -> dict:
    x, labels, unit_ids = trial_feature_matrix(state)
    all_labels = np.asarray(state.analysis["conditions"]).astype(str)
    valid_conditions = np.isin(all_labels, np.unique(labels))
    target_all = _reaction_time_target(state)
    if len(target_all) != len(all_labels):
        raise ValueError(
            "Continuous regression requires one reaction-time value per analyzed trial"
        )
    target = target_all[valid_conditions]
    finite = np.isfinite(target)
    x = x[finite]
    target = target[finite]
    if len(target) < 6:
        raise ValueError(
            "At least six trials with finite reaction time are required for regression"
        )
    folds = min(n_splits, len(target))
    model = clone(REGRESSION_MODELS[model_name])
    cv = KFold(n_splits=folds, shuffle=True, random_state=20260725)
    predictions = cross_val_predict(model, x, target, cv=cv, method="predict")
    fitted = clone(model).fit(x, target)
    if hasattr(fitted, "feature_importances_"):
        importance = fitted.feature_importances_
    elif hasattr(fitted, "named_steps") and hasattr(
        fitted.named_steps["model"], "coef_"
    ):
        importance = np.abs(np.asarray(fitted.named_steps["model"].coef_)).reshape(-1)
    else:
        importance = permutation_importance(
            fitted,
            x,
            target,
            scoring="r2",
            n_repeats=8,
            random_state=20260725,
            n_jobs=1,
        ).importances_mean
    result = {
        "model": model_name,
        "target": "reaction_time_seconds",
        "n_trials": len(target),
        "n_features": int(x.shape[1]),
        "cv_folds": folds,
        "r2": float(r2_score(target, predictions)),
        "mae_seconds": float(mean_absolute_error(target, predictions)),
        "rmse_seconds": float(np.sqrt(mean_squared_error(target, predictions))),
        "observed": target,
        "predicted": predictions,
        "residuals": target - predictions,
        "feature_importance": np.asarray(importance),
        "unit_ids": unit_ids,
        "available_models": list(REGRESSION_MODELS),
        "leakage_checks": [
            "Scaler and estimator are fitted independently inside each fold",
            "The continuous target is never used during feature construction",
            "For multi-session data, replace KFold with grouped splitting",
        ],
    }
    state.regression = result
    state.log(
        f"{model_name} completed: R2={result['r2']:.3f}, "
        f"MAE={result['mae_seconds']:.3f} s"
    )
    return result
