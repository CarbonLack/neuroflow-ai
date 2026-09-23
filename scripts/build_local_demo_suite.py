"""Build the three local, self-contained teaching projects and their reports.

The detector output is intentionally imperfect and is recorded as a synthetic
benchmark projection.  It must never be described as a real Kilosort run.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neuroflow.analysis import (  # noqa: E402
    compute_unit_metrics,
    event_aligned_analysis,
    export_reproducible_bundle,
    preprocessing_preview,
    run_raw_qc,
)
from neuroflow.decoding import run_decoding_suite  # noqa: E402
from neuroflow.ephys_toolkit import run_neural_toolkit  # noqa: E402
from neuroflow.project import save_project  # noqa: E402
from neuroflow.simulation import (  # noqa: E402
    DEMO_PROFILES,
    generate_demo_recording,
    simulate_sorter_output,
)
from neuroflow.sorting_results import (  # noqa: E402
    compare_sorting_results,
    register_sorting_result,
)
from neuroflow.statistics import run_statistical_suite  # noqa: E402
from neuroflow.synchronization import synchronize_existing_events  # noqa: E402


def build_one(root: Path, profile_key: str, duration_seconds: float) -> dict:
    profile = DEMO_PROFILES[profile_key]
    project = root / str(profile["folder"])
    state = generate_demo_recording(
        project,
        duration_seconds=duration_seconds,
        profile_key=profile_key,
    )
    state.metadata["language"] = "en_US"
    detected = simulate_sorter_output(
        state.ground_truth,
        state.duration_seconds,
        seed=2026092300 + list(DEMO_PROFILES).index(profile_key),
        native_id_offset=101 + 100 * list(DEMO_PROFILES).index(profile_key),
    )
    register_sorting_result(
        state,
        "synthetic_benchmark_detection",
        detected,
        {
            "sorter": "Synthetic imperfect benchmark detector",
            "backend": "NeuroEphys AI teaching-data generator",
            "version": "1",
            "warning": (
                "This result models missed events, timing jitter, false positives and "
                "cross-unit leakage. It is not output from Kilosort or another real sorter."
            ),
        },
    )
    compare_sorting_results(state)
    state.workflow_status["import"] = "completed"
    run_raw_qc(state)
    state.workflow_status["qc"] = "completed"
    preprocessing_preview(state)
    state.workflow_status["preprocess"] = "completed"
    state.workflow_status["sorting"] = "completed"
    compute_unit_metrics(state)
    state.workflow_status["unit_qc"] = "completed"
    synchronize_existing_events(state)
    state.workflow_status["sync"] = "completed"
    state.workflow_status["behavior"] = "completed"
    event_aligned_analysis(state)
    run_neural_toolkit(state)
    state.workflow_status["analysis"] = "completed"
    run_statistical_suite(state)
    state.workflow_status["statistics"] = "completed"
    decoding = run_decoding_suite(
        state,
        model_name="Logistic regression",
        n_splits=5,
        n_permutations=50,
    )
    state.workflow_status["decoding"] = (
        "completed" if decoding.get("status", "completed") != "failed" else "failed"
    )
    export_reproducible_bundle(state, state.root / "exports")
    state.workflow_status["export"] = "completed"
    save_project(state)
    matches = state.sorting_comparison.get("ground_truth", {}).get(
        "synthetic_benchmark_detection", {}
    )
    return {
        "profile": profile_key,
        "project": str(project),
        "duration_seconds": state.duration_seconds,
        "channels": state.channel_count,
        "truth_units": len(state.ground_truth),
        "display_units": len(state.sorted_spikes),
        "spike_count": int(sum(len(values) for values in state.sorted_spikes.values())),
        "event_count": len(state.events),
        "mean_sorting_f1": matches.get("mean_f1"),
        "decoding_status": decoding.get("status", "completed"),
        "decoding_auc": decoding.get(
            "roc_auc", decoding.get("auc_mean", decoding.get("auc"))
        ),
        "publication_storyboard": str(state.root / "exports/publication/storyboard.json"),
        "manifest": str(state.root / "neuroflow_project.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--profile", choices=[*DEMO_PROFILES, "all"], default="all")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    profiles = list(DEMO_PROFILES) if args.profile == "all" else [args.profile]
    rows = []
    for profile_key in profiles:
        print(f"BUILD {profile_key}", flush=True)
        rows.append(build_one(args.output, profile_key, args.duration))
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    report = {
        "schema": "neuroephys.local-demo-suite.v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "scope": "Locally generated synthetic teaching data; no published recording is bundled.",
        "projects": rows,
    }
    (args.output / "DEMO_SUITE_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output / "README.txt").write_text(
        """CURRENT LOCAL TEACHING SUITE
============================

This folder contains three complete, locally generated NeuroEphys AI projects:

1. Neuropixels_Decision: 32-channel staggered high-density probe.
2. Tetrode_Navigation: four tetrodes / 16 channels.
3. Microwire_Stimulus: 32 independent brush/microwire contacts; no spatial
   adjacency is inferred.

Open each neuroflow_project.json in the application. Every project contains raw
voltage, events, ground truth, an intentionally imperfect benchmark detection,
quality metrics, event analysis, statistics, decoding, plotting data, vector
publication figures, captions, parameters, and provenance.

The benchmark detection is not a real sorter result and is never presented as
Kilosort, MountainSort, WaveClus, or biological ground truth. It deliberately
contains missed spikes, false positives, time jitter, and slight cross-unit
leakage so ROC and quality figures are useful rather than artificially perfect.

No published recording is downloaded or bundled in this suite.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
