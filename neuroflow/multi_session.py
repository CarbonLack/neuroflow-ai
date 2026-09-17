"""Multi-session study aggregation, grouped decoding and latent dynamics.

The study layer deliberately treats trials as nested inside sessions and animals.
It never assumes that numeric unit ids identify the same neuron across sessions.
"""

from __future__ import annotations

import json
import math
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from .product import PRODUCT_NAME, PRODUCT_VERSION
from .project import MANIFEST_NAME, load_project

STUDY_MANIFEST_NAME = "neuroephys_study.json"
STUDY_SCHEMA = "neuroephys.multi_session_study.v1"
PURPLE = "#b99aca"
GREEN = "#a8d39d"
INK = "#20262d"
MUTED = "#6d7680"


@dataclass(slots=True)
class StudySession:
    project: str
    animal_id: str
    session_id: str
    included: bool = True
    notes: str = ""


@dataclass(slots=True)
class StudyState:
    root: Path
    name: str
    study_id: str = field(default_factory=lambda: secrets.token_hex(6))
    sessions: list[StudySession] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    run_log: list[str] = field(default_factory=list)

    @property
    def manifest_path(self) -> Path:
        return self.root / STUDY_MANIFEST_NAME

    def log(self, message: str) -> None:
        self.run_log.append(message)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def save_study(study: StudyState) -> Path:
    study.root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": STUDY_SCHEMA,
        "application": PRODUCT_NAME,
        "application_version": PRODUCT_VERSION,
        "study_id": study.study_id,
        "name": study.name,
        "sessions": [
            {
                "project": item.project,
                "animal_id": item.animal_id,
                "session_id": item.session_id,
                "included": item.included,
                "notes": item.notes,
            }
            for item in study.sessions
        ],
        "settings": _jsonable(study.settings),
        "results": _jsonable(study.results),
        "run_log": list(study.run_log),
    }
    temporary = study.manifest_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(study.manifest_path)
    return study.manifest_path


def load_study(path: Path) -> StudyState:
    manifest = path / STUDY_MANIFEST_NAME if path.is_dir() else path
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("schema") != STUDY_SCHEMA:
        raise ValueError("Unsupported or missing multi-session study schema")
    return StudyState(
        root=manifest.parent,
        name=str(payload.get("name", manifest.parent.name)),
        study_id=str(payload.get("study_id") or secrets.token_hex(6)),
        sessions=[StudySession(**row) for row in payload.get("sessions", [])],
        settings=dict(payload.get("settings", {})),
        results=payload.get("results", {}),
        run_log=list(payload.get("run_log", [])),
    )


def infer_session_identity(project_path: Path) -> tuple[str, str]:
    state = load_project(project_path)
    metadata = state.metadata
    animal = str(
        metadata.get("animal_id")
        or metadata.get("subject_id")
        or metadata.get("subject")
        or ""
    ).strip()
    session = str(
        metadata.get("session_id")
        or metadata.get("eid")
        or metadata.get("recording_id")
        or state.root.name
    ).strip()
    return animal, session


def add_project(
    study: StudyState,
    project_path: Path,
    animal_id: str,
    session_id: str,
) -> StudySession:
    manifest = project_path / MANIFEST_NAME if project_path.is_dir() else project_path
    manifest = manifest.resolve()
    if not manifest.is_file():
        raise FileNotFoundError(f"Project manifest not found: {manifest}")
    animal_id = animal_id.strip()
    session_id = session_id.strip()
    if not animal_id or not session_id:
        raise ValueError("Every included session requires animal_id and session_id")
    if any(Path(item.project).resolve() == manifest for item in study.sessions):
        raise ValueError("This project is already present in the study")
    if any(item.session_id == session_id for item in study.sessions):
        raise ValueError(f"session_id must be unique within a study: {session_id}")
    item = StudySession(str(manifest), animal_id, session_id)
    study.sessions.append(item)
    study.log(f"Added session {session_id} from animal {animal_id}")
    return item


def inspect_sessions(study: StudyState) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in study.sessions:
        row = {
            "animal_id": item.animal_id,
            "session_id": item.session_id,
            "included": item.included,
            "project": item.project,
            "status": "excluded" if not item.included else "ready",
            "trial_count": 0,
            "unit_count": 0,
            "conditions": [],
        }
        if not item.included:
            rows.append(row)
            continue
        try:
            state = load_project(Path(item.project))
            if not state.analysis or not state.analysis.get("units"):
                row["status"] = "event_analysis_required"
            else:
                row["trial_count"] = len(state.analysis.get("conditions", []))
                row["unit_count"] = len(state.analysis.get("units", {}))
                row["conditions"] = sorted(
                    set(map(str, state.analysis.get("conditions", [])))
                )
        except Exception as exc:  # noqa: BLE001 - inventory should report all rows
            row["status"] = f"error: {exc}"
        rows.append(row)
    return rows


def _moment_features(values: np.ndarray, response: np.ndarray) -> list[float]:
    finite = values[np.isfinite(values)]
    response_finite = response[np.isfinite(response)]
    if not len(finite) or not len(response_finite):
        return [math.nan] * 8
    return [
        float(np.mean(finite)),
        float(np.median(finite)),
        float(np.std(finite)),
        float(np.quantile(finite, 0.25)),
        float(np.quantile(finite, 0.75)),
        float(np.mean(finite > 0)),
        float(np.mean(response_finite)),
        float(np.std(response_finite)),
    ]


FEATURE_COLUMNS = [
    "delta_mean_hz",
    "delta_median_hz",
    "delta_std_hz",
    "delta_q25_hz",
    "delta_q75_hz",
    "positive_unit_fraction",
    "response_mean_hz",
    "response_std_hz",
]


def shared_conditions(study: StudyState) -> list[str]:
    """Return named conditions shared by every included, analyzed session."""
    condition_sets: list[set[str]] = []
    counts: dict[str, int] = {}
    for item in study.sessions:
        if not item.included:
            continue
        try:
            state = load_project(Path(item.project))
        except Exception:  # noqa: BLE001 - inventory remains usable after a move
            return []
        conditions = np.asarray(state.analysis.get("conditions", [])).astype(str)
        if not len(conditions):
            return []
        names = {
            condition
            for condition in conditions
            if condition.casefold() not in {"unknown", "nan", "none", ""}
        }
        condition_sets.append(names)
        for condition in names:
            counts[condition] = counts.get(condition, 0) + int(
                np.sum(conditions == condition)
            )
    if not condition_sets:
        return []
    common = set.intersection(*condition_sets)
    return sorted(common, key=lambda condition: (-counts.get(condition, 0), condition))


def build_trial_table(
    study: StudyState,
    selected_conditions: list[str] | tuple[str, str] | None = None,
) -> pd.DataFrame:
    """Create fixed-dimensional, unit-identity-invariant trial features."""
    rows: list[dict[str, Any]] = []
    condition_sets: list[set[str]] = []
    loaded: list[tuple[StudySession, Any]] = []
    for item in study.sessions:
        if not item.included:
            continue
        state = load_project(Path(item.project))
        analysis = state.analysis
        if not analysis or not analysis.get("units"):
            raise ValueError(
                f"Session {item.session_id} has no event-aligned analysis. "
                "Run event analysis in the single-session project first."
            )
        conditions = np.asarray(analysis.get("conditions", [])).astype(str)
        if not len(conditions):
            raise ValueError(f"Session {item.session_id} has no analyzed trials")
        condition_sets.append(set(conditions))
        loaded.append((item, state))
    if len(loaded) < 2:
        raise ValueError(
            "A multi-session study requires at least two included sessions"
        )
    common = set.intersection(*condition_sets)
    candidates: list[tuple[str, int]] = []
    for condition in common:
        count = sum(
            int(
                np.sum(
                    np.asarray(state.analysis["conditions"]).astype(str) == condition
                )
            )
            for _, state in loaded
        )
        if condition.casefold() not in {"unknown", "nan", "none"}:
            candidates.append((condition, count))
    candidates.sort(key=lambda item: item[1], reverse=True)
    if selected_conditions is None:
        selected = [condition for condition, _ in candidates[:2]]
    else:
        selected = [str(condition) for condition in selected_conditions]
        if len(selected) != 2 or selected[0] == selected[1]:
            raise ValueError("Select two different conditions")
        missing = sorted(set(selected) - common)
        if missing:
            raise ValueError(
                "Selected conditions are not shared by every included session: "
                + ", ".join(missing)
            )
    if len(selected) != 2:
        raise ValueError(
            "Two shared, named conditions are required across every included session"
        )
    for item, state in loaded:
        analysis = state.analysis
        centers = np.asarray(analysis["bin_centers"], dtype=float)
        baseline = tuple(analysis.get("baseline_window", (-0.5, 0.0)))
        response_window = tuple(analysis.get("response_window", (0.0, 0.5)))
        baseline_mask = (centers >= baseline[0]) & (centers < baseline[1])
        response_mask = (centers >= response_window[0]) & (centers < response_window[1])
        if not baseline_mask.any() or not response_mask.any():
            raise ValueError(f"Session {item.session_id} has empty analysis windows")
        unit_rates = np.stack(
            [
                np.asarray(unit["rates"], dtype=float)
                for unit in analysis["units"].values()
            ],
            axis=1,
        )
        conditions = np.asarray(analysis["conditions"]).astype(str)
        if unit_rates.shape[0] != len(conditions):
            raise ValueError(
                f"Session {item.session_id} trial dimensions are inconsistent"
            )
        for trial_index, condition in enumerate(conditions):
            if condition not in selected:
                continue
            trial_rates = unit_rates[trial_index]
            baseline_rates = trial_rates[:, baseline_mask].mean(axis=1)
            response_rates = trial_rates[:, response_mask].mean(axis=1)
            values = _moment_features(response_rates - baseline_rates, response_rates)
            row = {
                "animal_id": item.animal_id,
                "session_id": item.session_id,
                "condition": condition,
                "trial_index": int(trial_index),
                "unit_count": int(unit_rates.shape[1]),
            }
            row.update(dict(zip(FEATURE_COLUMNS, values)))
            rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty or frame[FEATURE_COLUMNS].isna().any(axis=None):
        raise ValueError("Multi-session feature extraction produced missing values")
    frame.attrs["selected_conditions"] = selected
    return frame


def _classifier(name: str):
    scaled = {
        "Logistic regression": LogisticRegression(
            max_iter=3000, class_weight="balanced", random_state=20260725
        ),
        "Linear SVM": SVC(
            kernel="linear",
            probability=True,
            class_weight="balanced",
            random_state=20260725,
        ),
        "RBF SVM": SVC(
            kernel="rbf",
            probability=True,
            class_weight="balanced",
            random_state=20260725,
        ),
        "Linear discriminant analysis": LinearDiscriminantAnalysis(
            shrinkage="auto", solver="lsqr"
        ),
    }
    if name in scaled:
        return Pipeline([("scale", StandardScaler()), ("model", scaled[name])])
    if name == "Random forest":
        return RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=20260725,
            n_jobs=1,
        )
    raise ValueError(f"Unknown multi-session classifier: {name}")


MULTI_SESSION_MODELS = [
    "Logistic regression",
    "Linear SVM",
    "RBF SVM",
    "Linear discriminant analysis",
    "Random forest",
]


def _valid_group_splits(x: np.ndarray, y: np.ndarray, groups: np.ndarray, folds: int):
    unique_groups = np.unique(groups)
    if len(unique_groups) < 2:
        raise ValueError("Grouped validation requires at least two groups")
    if folds >= len(unique_groups):
        splitter = LeaveOneGroupOut()
    else:
        try:
            splitter = StratifiedGroupKFold(
                n_splits=max(2, folds), shuffle=True, random_state=20260725
            )
        except TypeError:  # pragma: no cover - compatibility with older sklearn
            splitter = GroupKFold(n_splits=max(2, folds))
    valid = []
    for train, test in splitter.split(x, y, groups):
        if len(np.unique(y[train])) == 2 and len(np.unique(y[test])) == 2:
            valid.append((train, test))
    if len(valid) < 2:
        raise ValueError(
            "Grouped validation needs at least two held-out groups containing both conditions"
        )
    return valid


def _grouped_predictions(model, x, y, groups, splits):
    predictions = np.empty(len(y), dtype=int)
    probabilities = np.empty(len(y), dtype=float)
    covered = np.zeros(len(y), dtype=bool)
    fold_rows = []
    for fold, (train, test) in enumerate(splits, start=1):
        fitted = clone(model).fit(x[train], y[train])
        predicted = fitted.predict(x[test]).astype(int)
        if hasattr(fitted, "predict_proba"):
            probability = fitted.predict_proba(x[test])[:, 1]
        else:  # pragma: no cover - all registered models currently expose probability
            score = fitted.decision_function(x[test])
            probability = 1 / (1 + np.exp(-score))
        predictions[test] = predicted
        probabilities[test] = probability
        covered[test] = True
        fold_rows.append(
            {
                "fold": fold,
                "held_out_groups": sorted(set(map(str, groups[test]))),
                "n_test": len(test),
                "balanced_accuracy": float(balanced_accuracy_score(y[test], predicted)),
            }
        )
    return predictions[covered], probabilities[covered], covered, fold_rows


def _hierarchical_condition_effect(
    frame: pd.DataFrame, classes: list[str]
) -> dict[str, Any]:
    work = frame.copy()
    work["condition_binary"] = (work["condition"] == classes[1]).astype(float)
    session_summary = (
        work.groupby(["animal_id", "session_id", "condition"], as_index=False)[
            "delta_mean_hz"
        ]
        .mean()
        .rename(columns={"delta_mean_hz": "mean_population_delta_hz"})
    )
    result: dict[str, Any] = {
        "method": "descriptive_session_summary",
        "classes": classes,
        "session_summary": session_summary.to_dict(orient="records"),
        "warning": "",
    }
    if work["animal_id"].nunique() < 3:
        result["warning"] = (
            "Fewer than three animals are present; random-effect variance is not "
            "estimated. Session summaries are descriptive, not biological replicates."
        )
        return result
    try:
        import statsmodels.formula.api as smf

        model = smf.mixedlm(
            "delta_mean_hz ~ condition_binary",
            work,
            groups=work["animal_id"],
            vc_formula={"session": "0 + C(session_id)"},
            re_formula="1",
        )
        fitted = model.fit(reml=True, method="lbfgs", disp=False)
        ci = fitted.conf_int().loc["condition_binary"].tolist()
        result.update(
            {
                "method": "linear_mixed_effects",
                "fixed_effect_hz": float(fitted.params["condition_binary"]),
                "standard_error_hz": float(fitted.bse["condition_binary"]),
                "p_value": float(fitted.pvalues["condition_binary"]),
                "confidence_interval_95_hz": [float(ci[0]), float(ci[1])],
                "animal_random_intercept": True,
                "session_variance_component": True,
                "converged": bool(fitted.converged),
            }
        )
        if not fitted.converged:
            result["warning"] = (
                "The mixed-effects optimizer did not converge; do not interpret its p-value."
            )
    except Exception as exc:  # noqa: BLE001 - preserve descriptive output on fit failure
        result["warning"] = f"Mixed-effects fit was unavailable: {exc}"
    return result


def _population_moments(rates: np.ndarray) -> np.ndarray:
    """Convert units × time into a fixed time × population-moment trajectory."""
    return np.column_stack(
        [
            rates.mean(axis=0),
            rates.std(axis=0),
            np.quantile(rates, 0.25, axis=0),
            np.median(rates, axis=0),
            np.quantile(rates, 0.75, axis=0),
            (rates > 0).mean(axis=0),
        ]
    )


def run_latent_dynamics(
    study: StudyState,
    n_components: int = 3,
    selected_conditions: list[str] | tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Fit a transparent PCA + regularized linear state-transition model (LDM)."""
    sequences: list[np.ndarray] = []
    labels: list[dict[str, str]] = []
    time_axis: np.ndarray | None = None
    for item in study.sessions:
        if not item.included:
            continue
        state = load_project(Path(item.project))
        analysis = state.analysis
        if not analysis or not analysis.get("units"):
            raise ValueError(
                f"Session {item.session_id} needs event-aligned population activity"
            )
        centers = np.asarray(analysis.get("bin_centers", []), dtype=float)
        conditions = np.asarray(analysis.get("conditions", [])).astype(str)
        unit_rates = np.stack(
            [
                np.asarray(unit["rates"], dtype=float)
                for unit in analysis.get("units", {}).values()
            ],
            axis=1,
        )
        if not len(centers) or unit_rates.ndim != 3:
            raise ValueError(f"Session {item.session_id} lacks population time courses")
        if time_axis is None:
            time_axis = centers
        elif len(centers) != len(time_axis) or not np.allclose(centers, time_axis):
            raise ValueError(
                "All sessions need matching event-analysis time bins for LDM"
            )
        for condition in sorted(set(conditions)):
            if selected_conditions is not None and condition not in selected_conditions:
                continue
            selected = unit_rates[conditions == condition]
            if not len(selected):
                continue
            mean_units_time = selected.mean(axis=0)
            sequences.append(_population_moments(mean_units_time))
            labels.append(
                {
                    "animal_id": item.animal_id,
                    "session_id": item.session_id,
                    "condition": condition,
                }
            )
    if len(sequences) < 2 or time_axis is None:
        raise ValueError("LDM requires at least two session-condition trajectories")
    from sklearn.decomposition import PCA

    stacked = np.vstack(sequences)
    scaler = StandardScaler().fit(stacked)
    scaled = scaler.transform(stacked)
    components = min(n_components, scaled.shape[1], scaled.shape[0])
    pca = PCA(n_components=components, random_state=20260725).fit(scaled)
    transformed: list[np.ndarray] = []
    for sequence in sequences:
        transformed.append(pca.transform(scaler.transform(sequence)))
    previous = np.vstack([sequence[:-1] for sequence in transformed])
    following = np.vstack([sequence[1:] for sequence in transformed])
    transition = Ridge(alpha=1e-3, fit_intercept=True).fit(previous, following)
    predicted = transition.predict(previous)
    denominator = float(np.sum((following - following.mean(axis=0)) ** 2))
    r2 = 1 - float(np.sum((following - predicted) ** 2)) / max(denominator, 1e-12)
    eigenvalues = np.linalg.eigvals(transition.coef_.T)
    dt = float(np.median(np.diff(time_axis))) if len(time_axis) > 1 else math.nan
    timescales = []
    for value in eigenvalues:
        magnitude = abs(value)
        timescales.append(
            float(-dt / np.log(magnitude))
            if 0 < magnitude < 1 and np.isfinite(dt)
            else None
        )
    return {
        "schema": "neuroephys.latent_dynamics.v1",
        "method": "PCA plus ridge-regularized linear state transition",
        "interpretation": "Descriptive latent dynamics; not a deep generative model and not causal.",
        "time_seconds": time_axis,
        "labels": labels,
        "trajectories": np.asarray(transformed),
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "transition_matrix": transition.coef_.T,
        "transition_r2": float(r2),
        "eigenvalues_real": np.real(eigenvalues),
        "eigenvalues_imag": np.imag(eigenvalues),
        "timescales_seconds": timescales,
    }


def run_multi_session_analysis(
    study: StudyState,
    model_name: str = "Linear SVM",
    group_by: str = "auto",
    n_splits: int = 5,
    n_permutations: int = 200,
    selected_conditions: list[str] | tuple[str, str] | None = None,
) -> dict[str, Any]:
    frame = build_trial_table(study, selected_conditions=selected_conditions)
    if model_name not in MULTI_SESSION_MODELS:
        raise ValueError(f"Model is not registered: {model_name}")
    if group_by not in {"auto", "animal", "session"}:
        raise ValueError("group_by must be auto, animal, or session")
    animal_count = frame["animal_id"].nunique()
    chosen_group = (
        "animal"
        if group_by == "auto" and animal_count >= 2
        else "session"
        if group_by == "auto"
        else group_by
    )
    if chosen_group == "animal" and animal_count < 2:
        raise ValueError("Cross-animal validation requires at least two animals")
    group_column = "animal_id" if chosen_group == "animal" else "session_id"
    x = frame[FEATURE_COLUMNS].to_numpy(dtype=float)
    classes = list(
        frame.attrs.get("selected_conditions") or sorted(frame["condition"].unique())
    )
    y = (frame["condition"].to_numpy() == classes[1]).astype(int)
    groups = frame[group_column].astype(str).to_numpy()
    splits = _valid_group_splits(x, y, groups, min(n_splits, len(np.unique(groups))))
    model = _classifier(model_name)
    predictions, probabilities, covered, fold_rows = _grouped_predictions(
        model, x, y, groups, splits
    )
    observed = y[covered]
    score = float(balanced_accuracy_score(observed, predictions))
    auc = float(roc_auc_score(observed, probabilities))
    rng = np.random.default_rng(20260725)
    null_scores = []
    permutation_groups = frame["session_id"].astype(str).to_numpy()
    for _ in range(max(0, int(n_permutations))):
        shuffled = y.copy()
        for group in np.unique(permutation_groups):
            indices = np.flatnonzero(permutation_groups == group)
            shuffled[indices] = rng.permutation(shuffled[indices])
        null_predictions, _, null_covered, _ = _grouped_predictions(
            model, x, shuffled, groups, splits
        )
        null_scores.append(
            float(balanced_accuracy_score(shuffled[null_covered], null_predictions))
        )
    permutation_p = (
        float((1 + np.sum(np.asarray(null_scores) >= score)) / (1 + len(null_scores)))
        if null_scores
        else math.nan
    )
    covered_groups = groups[covered]
    held_out_group_rows = []
    for group in sorted(set(map(str, covered_groups))):
        selected = covered_groups == group
        if len(np.unique(observed[selected])) != 2:
            continue
        held_out_group_rows.append(
            {
                "group": group,
                "n_test": int(np.sum(selected)),
                "balanced_accuracy": float(
                    balanced_accuracy_score(observed[selected], predictions[selected])
                ),
            }
        )
    group_scores = np.asarray([row["balanced_accuracy"] for row in held_out_group_rows])
    if len(group_scores) < 2:
        raise ValueError(
            "At least two held-out groups with both conditions are needed for uncertainty."
        )
    bootstrap_rng = np.random.default_rng(20260726)
    bootstrap = np.asarray(
        [
            bootstrap_rng.choice(
                group_scores, size=len(group_scores), replace=True
            ).mean()
            for _ in range(2000)
        ]
    )
    prediction_rows = frame.loc[
        covered, ["animal_id", "session_id", "condition", "trial_index"]
    ].copy()
    prediction_rows["predicted_condition"] = [classes[index] for index in predictions]
    prediction_rows["probability_second_condition"] = probabilities
    result = {
        "schema": "neuroephys.multi_session_analysis.v1",
        "study_id": study.study_id,
        "study_name": study.name,
        "model": model_name,
        "classes": classes,
        "group_by": chosen_group,
        "validation": (
            "leave-one-group-out"
            if len(splits) == len(np.unique(groups))
            else "stratified-group-k-fold"
        ),
        "animal_count": int(frame["animal_id"].nunique()),
        "session_count": int(frame["session_id"].nunique()),
        "trial_count": len(frame),
        "feature_columns": FEATURE_COLUMNS,
        "feature_policy": (
            "Population distribution features; unit ids are not matched across sessions."
        ),
        "selected_conditions": classes,
        "balanced_accuracy": score,
        "roc_auc": auc,
        "permutation_p": permutation_p,
        "permutation_group_by": "session",
        "null_scores": null_scores,
        "confidence_interval_95": [
            float(np.quantile(bootstrap, 0.025)),
            float(np.quantile(bootstrap, 0.975)),
        ],
        "confidence_interval_method": "held-out-group bootstrap",
        "confusion_matrix": confusion_matrix(observed, predictions, labels=[0, 1]),
        "held_out_group_metrics": fold_rows,
        "held_out_group_scores": held_out_group_rows,
        "predictions": prediction_rows.to_dict(orient="records"),
        "hierarchical_condition_effect": _hierarchical_condition_effect(frame, classes),
        "latent_dynamics": run_latent_dynamics(study, selected_conditions=classes),
        "safeguards": [
            "Trials from one validation group never appear in both train and test.",
            "Label permutations occur within sessions, preserving the nested structure.",
            "Unit ids are not assumed to match across sessions.",
            "Animal-level inference is withheld when fewer than two animals are present.",
        ],
        "interpretation": {
            "supports": (
                "Predictive information that generalizes to held-out "
                f"{chosen_group}s under the recorded conditions."
            ),
            "does_not_support": (
                "Causality, stable identity of individual neurons across sessions, "
                "or generalization beyond the sampled animals and sessions."
            ),
            "ldm": (
                "The latent-dynamics panel is a descriptive PCA plus linear state "
                "transition summary; it is not a deep generative or causal model."
            ),
        },
    }
    study.settings.update(
        {
            "model": model_name,
            "group_by": group_by,
            "cv_folds": int(n_splits),
            "permutations": int(n_permutations),
            "conditions": classes,
        }
    )
    study.results = result
    study.log(
        f"{model_name} multi-session analysis: balanced accuracy={score:.3f}, "
        f"grouped by {chosen_group}, permutation p={permutation_p:.4f}"
    )
    save_study(study)
    export_study_results(study, frame)
    return result


def study_figure(study: StudyState):
    result = study.results
    if not result:
        raise ValueError("Run multi-session analysis first")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.8), constrained_layout=True)
    groups = result["held_out_group_scores"]
    labels = [row["group"] for row in groups]
    scores = [row["balanced_accuracy"] for row in groups]
    axes[0, 0].bar(np.arange(len(scores)), scores, color=PURPLE, edgecolor="white")
    axes[0, 0].axhline(0.5, color=MUTED, linestyle="--", linewidth=1)
    axes[0, 0].set_xticks(np.arange(len(labels)), labels, rotation=35, ha="right")
    axes[0, 0].set_ylim(0, 1)
    axes[0, 0].set_ylabel("Balanced accuracy")
    axes[0, 0].set_title("Held-out group decoding", loc="left")
    matrix = np.asarray(result["confusion_matrix"], dtype=float)
    normalized = matrix / np.maximum(matrix.sum(axis=1, keepdims=True), 1)
    axes[0, 1].imshow(normalized, cmap="Purples", vmin=0, vmax=1)
    for row in range(2):
        for column in range(2):
            axes[0, 1].text(
                column,
                row,
                f"{matrix[row, column]:.0f}\n{normalized[row, column]:.0%}",
                ha="center",
                va="center",
            )
    axes[0, 1].set_xticks([0, 1], result["classes"])
    axes[0, 1].set_yticks([0, 1], result["classes"])
    axes[0, 1].set_xlabel("Predicted")
    axes[0, 1].set_ylabel("Observed")
    axes[0, 1].set_title("Grouped confusion matrix", loc="left")
    summary = pd.DataFrame(result["hierarchical_condition_effect"]["session_summary"])
    for condition, color in zip(result["classes"], [PURPLE, GREEN]):
        selected = summary[summary["condition"] == condition]
        axes[1, 0].scatter(
            selected["session_id"],
            selected["mean_population_delta_hz"],
            label=condition,
            color=color,
            s=34,
        )
    axes[1, 0].tick_params(axis="x", rotation=35)
    axes[1, 0].set_ylabel("Population response − baseline (Hz)")
    axes[1, 0].set_title("Session-level condition effects", loc="left")
    axes[1, 0].legend(frameon=False)
    ldm = result["latent_dynamics"]
    trajectories = np.asarray(ldm["trajectories"], dtype=float)
    for trajectory, label in zip(trajectories, ldm["labels"]):
        color = PURPLE if label["condition"] == result["classes"][0] else GREEN
        axes[1, 1].plot(
            trajectory[:, 0],
            trajectory[:, 1] if trajectory.shape[1] > 1 else np.zeros(len(trajectory)),
            color=color,
            alpha=0.55,
            linewidth=1.2,
        )
    axes[1, 1].set_xlabel("Latent dimension 1")
    axes[1, 1].set_ylabel("Latent dimension 2")
    axes[1, 1].set_title(
        f"Latent dynamics · transition R²={ldm['transition_r2']:.2f}", loc="left"
    )
    for ax in axes.flat:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(False)
        ax.tick_params(colors=INK)
    return fig


def export_study_results(
    study: StudyState, trial_table: pd.DataFrame | None = None
) -> Path:
    if not study.results:
        raise ValueError("Run multi-session analysis first")
    output = study.root / "results" / "multi_session"
    output.mkdir(parents=True, exist_ok=True)
    if trial_table is None:
        trial_table = build_trial_table(study)
    trial_table.to_csv(output / "trial_features.csv", index=False)
    pd.DataFrame(
        study.results["hierarchical_condition_effect"]["session_summary"]
    ).to_csv(output / "session_condition_summary.csv", index=False)
    pd.DataFrame(study.results["held_out_group_metrics"]).to_csv(
        output / "held_out_group_metrics.csv", index=False
    )
    pd.DataFrame(study.results["held_out_group_scores"]).to_csv(
        output / "held_out_group_scores.csv", index=False
    )
    pd.DataFrame(study.results["predictions"]).to_csv(
        output / "grouped_decoding_predictions.csv", index=False
    )
    (output / "multi_session_results.json").write_text(
        json.dumps(_jsonable(study.results), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    figure = study_figure(study)
    figure.savefig(output / "multi_session_summary.svg", bbox_inches="tight")
    figure.savefig(output / "multi_session_summary.png", dpi=600, bbox_inches="tight")
    plt.close(figure)
    return output
