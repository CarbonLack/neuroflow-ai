"""Prepare and run publication-style multi-session benchmark studies.

The normal benchmark projects intentionally cannot see simulation ground truth.  This
validation script is the explicit exception: it creates small analysis projects in a
separate user-project directory, registers the external truth as a clearly labelled
validation reference, performs event alignment, and runs the Study suite.  Raw voltage
is never copied or modified.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from neuroflow.analysis import event_aligned_analysis
from neuroflow.multi_session import StudyState, add_project, run_multi_session_analysis, save_study
from neuroflow.project import load_project, save_project


def _truth(path: Path) -> dict[int, np.ndarray]:
    with np.load(path) as archive:
        return {
            int(key.rsplit("_", 1)[-1]): np.asarray(archive[key], dtype=float)
            for key in archive.files
        }


def prepare_session(
    source: Path,
    truth: Path,
    destination: Path,
    electrode: str,
    session_id: str,
) -> Path:
    state = load_project(source)
    spikes = _truth(truth / "true_spike_times.npz")
    state.root = destination
    state.name = f"{electrode.title()} benchmark {session_id} · validation reference"
    state.ground_truth = {}
    state.sorted_spikes = spikes
    state.sorting_results = {"simulation_truth_validation_reference": spikes}
    state.active_sorter_key = "simulation_truth_validation_reference"
    state.sorting_provenance = {
        "simulation_truth_validation_reference": {
            "role": "benchmark_validation_only",
            "source": str(truth / "true_spike_times.npz"),
            "warning": (
                "This is deterministic simulation truth, not a sorter result and not "
                "evidence of accuracy on biological recordings."
            ),
        }
    }
    state.analysis = {}
    state.metadata = {
        **state.metadata,
        "session_id": session_id,
        "subject_id": "simulated_subject_unassigned",
        "multi_session_validation_role": "simulation_ground_truth_workflow_validation",
        "biological_replication": False,
        "raw_data_copied": False,
        "source_project": str(source),
    }
    state.run_log = list(state.run_log) + [
        "External simulation truth was registered only for explicit multi-session "
        "workflow validation; it was not exposed to the ordinary benchmark project."
    ]
    event_aligned_analysis(
        state,
        window=(-0.5, 1.0),
        bin_size=0.025,
        conditions=["lever_press", "reward_delivery"],
    )
    state.workflow_status = {
        **state.workflow_status,
        "sorting": "simulation_truth_validation_reference",
        "event_analysis": "completed",
    }
    return save_project(state)


def run_family(
    benchmark: Path,
    output_parent: Path,
    electrode: str,
    permutations: int,
) -> Path:
    study_root = output_parent / f"{electrode.title()}_20min_Multi_Session_Study"
    prepared = study_root / "Prepared_Sessions"
    study = StudyState(study_root, f"{electrode.title()} 20-minute benchmark study")
    for index in range(1, 8):
        session_id = f"session_{index:02d}"
        manifest = prepare_session(
            benchmark / electrode / session_id,
            benchmark / "ground_truth" / electrode / session_id,
            prepared / session_id,
            electrode,
            session_id,
        )
        add_project(
            study,
            manifest,
            animal_id="simulated_subject_unassigned",
            session_id=session_id,
        )
    study.settings["data_scope"] = {
        "electrode": electrode,
        "sessions": 7,
        "duration_per_session_minutes": 20,
        "biological_animal_ids_available": False,
        "inference_unit": "session",
    }
    save_study(study)
    run_multi_session_analysis(
        study,
        model_name="Linear SVM",
        group_by="session",
        n_splits=7,
        n_permutations=permutations,
        selected_conditions=["lever_press", "reward_delivery"],
    )
    readme = [
        f"# {study.name}",
        "",
        "This folder is a complete NeuroEphys AI Study for seven deterministic 20-minute "
        f"{electrode} simulations. Raw recordings remain in the canonical Example Projects "
        "collection and are referenced read-only; they are not duplicated here.",
        "",
        "`Prepared_Sessions/` contains analysis-ready project manifests and derived event "
        "responses. `results/multi_session/` contains the English main figure, supplementary "
        "controls, CSV matrices, JSON, and `INTERPRETATION.md`.",
        "",
        "All sessions use the external deterministic simulation truth solely to validate the "
        "analysis workflow. It is not a sorter result, a biological animal cohort, or evidence "
        "of performance on real recordings. Because the generator has no animal identifiers, "
        "all inference holds out complete sessions and no cross-animal claim is made.",
    ]
    (study_root / "README.md").write_text("\n".join(readme), encoding="utf-8")
    return study.manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--permutations", type=int, default=200)
    parser.add_argument(
        "--electrode", choices=["tetrode", "neuropixels", "both"], default="both"
    )
    args = parser.parse_args()
    families = ("tetrode", "neuropixels") if args.electrode == "both" else (args.electrode,)
    for electrode in families:
        manifest = run_family(
            args.benchmark.resolve(), args.output.resolve(), electrode, args.permutations
        )
        print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
