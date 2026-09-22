"""Finish a saved, real MED-PC project without inventing unavailable analyses."""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use("Agg")

from neuroflow.analysis import event_aligned_analysis, export_reproducible_bundle
from neuroflow.decoding import decoding_input_diagnostics, run_decoding_suite
from neuroflow.ephys_toolkit import run_neural_toolkit
from neuroflow.project import load_project, save_project
from neuroflow.statistics import run_statistical_suite


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    state = load_project(args.project)
    if not state.sorted_spikes or not state.events:
        raise ValueError("A completed sorting result and imported behavioral events are required")
    records = []

    def stage(name, operation):
        started = datetime.now().astimezone().isoformat()
        try:
            detail = operation()
            row = {"stage": name, "status": "completed", "started_at": started,
                   "detail": detail if isinstance(detail, (str, int, float, bool, dict)) else str(detail)}
        except Exception as exc:
            row = {"stage": name, "status": "failed", "started_at": started,
                   "error": str(exc), "traceback": traceback.format_exc()}
        records.append(row)
        state.metadata.setdefault("complete_analysis_audit", []).append(row)
        save_project(state)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        return row

    # The Left/Right light-on family is a documented, interpretable two-choice
    # alignment. All other event families are exported separately by the
    # event-family script; no class labels are inferred from spike activity.
    def align():
        value = event_aligned_analysis(state, event_codes=[5, 7])
        return {"selected_event_count": value.get("selected_event_count"),
                "event_codes": [5, 7], "scope": "left/right light-on events"}

    aligned = stage("event_alignment", align)
    if aligned["status"] == "completed":
        stage("neural_activity", lambda: {
            "branches": list(run_neural_toolkit(state)),
            "lfp_exclusion": state.metadata.get("acquisition_preprocessing", {}).get("lfp_unavailable_reason"),
        })
        stage("statistics", lambda: {
            "significant_count": run_statistical_suite(state).get("significant_count"),
            "scope": "candidate units; not manually accepted single cells",
        })
        diagnostic = decoding_input_diagnostics(state)
        if diagnostic["status"] == "ready":
            stage("decoding", lambda: {
                "status": run_decoding_suite(state, "Logistic regression", n_permutations=100).get("status", "completed"),
                "input_diagnostics": diagnostic,
            })
        else:
            row = {"stage": "decoding", "status": "not_applicable", "detail": diagnostic}
            records.append(row)
            state.metadata.setdefault("complete_analysis_audit", []).append(row)
            save_project(state)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    stage("publication_export", lambda: str(export_reproducible_bundle(state, state.root / "exports")))
    report = state.root / "exports" / "complete_analysis_report.json"
    report.write_text(json.dumps({
        "schema": "neuroephys.real-session-analysis.v1",
        "project": state.name,
        "subject": state.metadata.get("subject_identity"),
        "source_type": state.source_type,
        "recording_duration_seconds": state.duration_seconds,
        "candidate_unit_count": len(state.sorted_spikes),
        "behavior_event_count": len(state.events),
        "sync": {
            key: state.metadata.get("synchronization", {}).get(key)
            for key in (
                "status", "method", "behavior_anchor_count", "ttl_event_count",
                "matched_count", "drift_ppm", "mean_abs_residual_ms",
            )
        },
        "stages": records,
        "additional_checks": {
            "event_family_summary": "event_analysis_summary.json",
            "event_family_correction": "event_family_review/event_family_tests.json",
            "external_reference_comparison": "nex5_reference_comparison.json",
            "scientific_interpretation": "SCIENTIFIC_INTERPRETATION.md",
        },
        "interpretation_limits": [
            "Candidate clusters are not biologically validated single units.",
            "A single animal and session cannot establish cross-animal generalization.",
            "An acquisition high-pass at 300 Hz makes low-frequency LFP analyses unavailable.",
            "Any existing Offline Sorter NEX5 result is a reference sorting, not ground truth.",
        ],
        "publication_html": "publication/index.html",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    save_project(state)
    if any(row["status"] == "failed" for row in records):
        raise RuntimeError(f"One or more analyses failed; inspect {report}")


if __name__ == "__main__":
    main()
