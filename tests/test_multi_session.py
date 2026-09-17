from pathlib import Path

import numpy as np
import pytest

from neuroephys.cli import main
from neuroflow.models import ProjectState
from neuroflow.multi_session import (
    STUDY_MANIFEST_NAME,
    StudyState,
    add_project,
    build_trial_table,
    load_study,
    run_multi_session_analysis,
    save_study,
    shared_conditions,
)
from neuroflow.project import save_project


def _session(root: Path, animal: str, session: str, seed: int) -> Path:
    rng = np.random.default_rng(seed)
    conditions = np.asarray(["control", "choice"] * 10)
    centers = np.linspace(-0.45, 0.45, 10)
    units = {}
    for unit_id in range(7 + seed % 3):
        rates = rng.uniform(1, 4, size=(len(conditions), len(centers)))
        rates[np.ix_(conditions == "choice", centers >= 0)] += 4.0 + 0.2 * unit_id
        units[unit_id] = {"rates": rates}
    state = ProjectState(
        root=root,
        name=session,
        source_type="test",
        sorted_spikes={0: np.asarray([0.1])},
        analysis={
            "conditions": conditions,
            "bin_centers": centers,
            "baseline_window": (-0.5, 0.0),
            "response_window": (0.0, 0.5),
            "units": units,
        },
        metadata={"animal_id": animal, "session_id": session},
    )
    return save_project(state)


def test_multi_session_grouped_decoding_and_ldm(tmp_path: Path):
    study = StudyState(tmp_path / "study", "Cross-session test")
    for index, (animal, session) in enumerate(
        [("a1", "s1"), ("a1", "s2"), ("a2", "s3"), ("a2", "s4")]
    ):
        manifest = _session(tmp_path / session, animal, session, index + 1)
        add_project(study, manifest, animal, session)
    save_study(study)
    restored = load_study(study.root / STUDY_MANIFEST_NAME)
    frame = build_trial_table(restored)
    assert len(frame) == 80
    assert frame["session_id"].nunique() == 4
    assert "unit_id" not in frame.columns
    assert shared_conditions(restored) == ["choice", "control"]

    result = run_multi_session_analysis(
        restored,
        model_name="Linear SVM",
        group_by="animal",
        n_permutations=10,
        selected_conditions=["control", "choice"],
    )
    assert result["group_by"] == "animal"
    assert result["animal_count"] == 2
    assert result["session_count"] == 4
    assert result["balanced_accuracy"] > 0.8
    assert result["latent_dynamics"]["schema"] == "neuroephys.latent_dynamics.v1"
    assert result["selected_conditions"] == ["control", "choice"]
    assert "Unit ids are not assumed" in " ".join(result["safeguards"])
    output = restored.root / "results" / "multi_session"
    assert (output / "trial_features.csv").is_file()
    assert (output / "multi_session_results.json").is_file()
    assert (output / "multi_session_summary.svg").is_file()
    saved = load_study(restored.manifest_path)
    assert saved.settings["conditions"] == ["control", "choice"]


def test_one_animal_withholds_animal_inference(tmp_path: Path):
    study = StudyState(tmp_path / "study", "One animal")
    for index, session in enumerate(("s1", "s2", "s3")):
        manifest = _session(tmp_path / session, "a1", session, index + 10)
        add_project(study, manifest, "a1", session)
    result = run_multi_session_analysis(
        study,
        model_name="Linear discriminant analysis",
        group_by="auto",
        n_permutations=2,
    )
    assert result["group_by"] == "session"
    hierarchy = result["hierarchical_condition_effect"]
    assert hierarchy["method"] == "descriptive_session_summary"
    assert "fewer than three animals" in hierarchy["warning"].lower()


@pytest.mark.parametrize(
    "model",
    [
        "Logistic regression",
        "Linear SVM",
        "RBF SVM",
        "Linear discriminant analysis",
        "Random forest",
    ],
)
def test_all_registered_study_classifiers_run(tmp_path: Path, model: str):
    study = StudyState(tmp_path / "study", "Model registry")
    for index, (animal, session) in enumerate(
        [("a1", "s1"), ("a1", "s2"), ("a2", "s3"), ("a2", "s4")]
    ):
        add_project(
            study,
            _session(tmp_path / session, animal, session, index + 31),
            animal,
            session,
        )
    result = run_multi_session_analysis(
        study,
        model_name=model,
        group_by="animal",
        n_permutations=0,
        selected_conditions=["control", "choice"],
    )
    assert result["model"] == model
    assert 0 <= result["balanced_accuracy"] <= 1


def test_multi_session_cli_inspects_and_runs_selected_conditions(
    tmp_path: Path,
    capsys,
):
    study = StudyState(tmp_path / "study", "CLI study")
    for index, (animal, session) in enumerate(
        [("a1", "s1"), ("a1", "s2"), ("a2", "s3"), ("a2", "s4")]
    ):
        add_project(
            study,
            _session(tmp_path / session, animal, session, index + 21),
            animal,
            session,
        )
    save_study(study)

    assert main(["study-inspect", str(study.root), "--json"]) == 0
    inventory = capsys.readouterr().out
    assert '"sessions"' in inventory
    assert (
        main(
            [
                "study-run",
                str(study.root),
                "--group-by",
                "animal",
                "--permutations",
                "0",
                "--conditions",
                "control",
                "choice",
                "--json",
            ]
        )
        == 0
    )
    assert '"balanced_accuracy"' in capsys.readouterr().out
