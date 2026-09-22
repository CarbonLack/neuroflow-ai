"""Compare external NEX5 sorting with one project's candidates, never as GT."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from neuroflow.nex5_adapter import _read_units
from neuroflow.project import load_project


def _coincidence_fraction(reference: np.ndarray, candidate: np.ndarray,
                          tolerance_s: float = 0.0005) -> float:
    if not len(reference) or not len(candidate):
        return 0.0
    indices = np.searchsorted(candidate, reference)
    right = np.clip(indices, 0, len(candidate) - 1)
    left = np.clip(indices - 1, 0, len(candidate) - 1)
    nearest = np.minimum(np.abs(candidate[right] - reference),
                         np.abs(candidate[left] - reference))
    return float(np.mean(nearest <= tolerance_s))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--first-acquisition-channel", type=int, default=33)
    args = parser.parse_args()
    state = load_project(args.project)
    folder = state.root / "inputs" / "reference_sorting"
    paths = sorted(folder.glob("*.nex5"))
    if not paths:
        raise ValueError("No locally archived NEX5 reference files")
    references = {}
    alignments = {}
    for mode in ("preserve", "auto_project_duration"):
        units, summary, _ = _read_units(paths, project_duration=state.duration_seconds,
                                       project_is_segment=False, alignment_mode=mode,
                                       manual_offset_seconds=0.0)
        references[mode] = units
        alignments[mode] = summary
    rows = []
    for unshifted, aligned in zip(references["preserve"], references["auto_project_duration"]):
        if unshifted.source_variable != aligned.source_variable:
            raise RuntimeError("Reference Unit order differs between alignment passes")
        channel = aligned.channel_number
        if channel is None or not 33 <= channel <= 64:
            raise ValueError(f"Reference Unit {aligned.source_variable} falls outside confirmed subject 102 channels")
        candidate_rows = []
        for metric in state.unit_metrics:
            if int(metric.get("peak_channel", -100)) + args.first_acquisition_channel != channel:
                continue
            unit_id = int(metric["unit_id"])
            spikes = np.asarray(state.sorted_spikes[unit_id], dtype=float)
            candidate_rows.append({
                "candidate_unit": unit_id,
                "candidate_spikes": len(spikes),
                "preserved_clock_fraction": _coincidence_fraction(unshifted.timestamps_seconds, spikes),
                "end_aligned_fraction": _coincidence_fraction(aligned.timestamps_seconds, spikes),
            })
        candidate_rows.sort(key=lambda row: row["end_aligned_fraction"], reverse=True)
        rows.append({
            "reference_file": aligned.source_file.name,
            "reference_variable": aligned.source_variable,
            "acquisition_channel": channel,
            "reference_spikes_preserved": len(unshifted.timestamps_seconds),
            "reference_spikes_end_aligned": len(aligned.timestamps_seconds),
            "same_contact_candidates": candidate_rows,
        })
    files = []
    for path in paths:
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest})
    report = {
        "schema": "neuroephys.reference-sorting-comparison.v1",
        "purpose": "External Offline Sorter comparison, not biological ground truth or accuracy",
        "subject_mapping": "Subject 102 = acquisition channels 33-64, user-confirmed",
        "reference_scope": "Only NEX5 neuron names CH33-CH64; matching session filenames require researcher confirmation",
        "time_tolerance_seconds": 0.0005,
        "alignment_hypotheses": {key: {"files": [{"path": Path(f["path"]).name,
            "alignment_offset_seconds": f["alignment_offset_seconds"],
            "alignment_method": f["alignment_method"],
            "warnings": f["warnings"]} for f in value["files"]]}
            for key, value in alignments.items()},
        "limitations": [
            "Document-end alignment is a hypothesis, not hardware-TTL verified synchronization.",
            "Same-contact spike coincidence reflects agreement, not precision/recall against ground truth.",
            "Different preprocessing, thresholds and manual curation can create legitimate disagreements.",
        ],
        "reference_files": files,
        "units": rows,
    }
    output = state.root / "exports" / "nex5_reference_comparison.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "reference_units": len(rows),
                      "same_contact_comparisons": sum(len(row["same_contact_candidates"]) for row in rows)},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
