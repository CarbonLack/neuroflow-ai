from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neuroflow.analysis import event_aligned_analysis
from neuroflow.data_import import import_ibl_alf, import_nwb_units
from neuroflow.decoding import run_decoding_suite
from neuroflow.figures import (
    behavior_figure,
    decoding_figure,
    event_analysis_figure,
    statistics_figure,
)
from neuroflow.sorting_results import register_sorting_result
from neuroflow.statistics import run_statistical_suite

IBL_EID = "4ecb5d24-f5cc-402c-be28-9d0f7cb14b3a"
IBL_PID = "da8dfec1-d265-44e8-84ce-6ae9c109b8bd"
DANDISET = "000552"
DANDI_VERSION = "0.230630.2304"
DANDI_ASSET = "f36a3ffe-1aa2-4019-a8fc-07b03bb2b38e"


def _save_figures(state, output: Path, prefix: str) -> None:
    figures = {
        "behavior": behavior_figure(state),
        "event": event_analysis_figure(state),
        "statistics": statistics_figure(state),
        "decoding": decoding_figure(state),
    }
    for name, figure in figures.items():
        figure.savefig(
            output / f"{prefix}_{name}.png",
            dpi=180,
            bbox_inches="tight",
        )


def validate_ibl(alf: Path, output: Path, permutations: int) -> dict:
    state = import_ibl_alf(output / "ibl_verified_project", alf)
    full_units = len(state.sorted_spikes)
    full_spikes = sum(len(values) for values in state.sorted_spikes.values())
    selected = dict(
        sorted(
            state.sorted_spikes.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        )[:64]
    )
    register_sorting_result(
        state,
        "ibl_validation_subset_64",
        selected,
        {
            "sorter": "IBL processed sorting validation subset",
            "backend": "IBL ALF",
            "selection": (
                "64 units with most spikes; computational integration validation only"
            ),
        },
    )
    event_aligned_analysis(state)
    statistical = run_statistical_suite(state)
    decoding = run_decoding_suite(state, n_permutations=permutations)
    _save_figures(state, output, "ibl")
    return {
        "eid": IBL_EID,
        "pid": IBL_PID,
        "probe": "probe00",
        "units_imported": full_units,
        "spikes_imported": full_spikes,
        "trials": len(state.trials),
        "events": len(state.events),
        "validated_units": len(selected),
        "statistics_rows": len(statistical["rows"]),
        "significant_fdr": statistical["significant_count"],
        "balanced_accuracy": decoding["balanced_accuracy"],
        "permutation_p": decoding["permutation_p"],
        "scope": "software integration validation, not a paper-level reproduction",
    }


def validate_buzsaki(nwb: Path, output: Path, permutations: int) -> dict:
    state = import_nwb_units(output / "buzsaki_verified_project", nwb)
    event_aligned_analysis(state)
    statistical = run_statistical_suite(state)
    decoding = run_decoding_suite(state, n_permutations=permutations)
    _save_figures(state, output, "buzsaki")
    return {
        "dandiset": DANDISET,
        "version": DANDI_VERSION,
        "asset_id": DANDI_ASSET,
        "units": len(state.sorted_spikes),
        "spikes": sum(len(values) for values in state.sorted_spikes.values()),
        "events": len(state.events),
        "sleep_states": len(state.metadata["intervals"].get("sleep_states", [])),
        "ripples": len(state.metadata["intervals"].get("ripples", [])),
        "statistics_rows": len(statistical["rows"]),
        "constant_condition_rows": sum(
            row["condition_test_status"] != "tested"
            for row in statistical["rows"]
        ),
        "significant_fdr": statistical["significant_count"],
        "balanced_accuracy": decoding["balanced_accuracy"],
        "permutation_p": decoding["permutation_p"],
        "scope": "software integration validation, not a paper-level reproduction",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate NeuroFlow against fixed IBL and Buzsáki public sessions."
    )
    parser.add_argument("--ibl-alf", type=Path, required=True)
    parser.add_argument("--buzsaki-nwb", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("public_validation"))
    parser.add_argument(
        "--permutations",
        type=int,
        default=20,
        help="Use at least 1000 for inferential work; 20 is a fast integration test.",
    )
    args = parser.parse_args()
    if not args.ibl_alf.is_dir():
        raise SystemExit(f"IBL ALF folder not found: {args.ibl_alf}")
    if not args.buzsaki_nwb.is_file():
        raise SystemExit(f"Buzsáki NWB file not found: {args.buzsaki_nwb}")
    args.output.mkdir(parents=True, exist_ok=True)
    result = {
        "ibl": validate_ibl(args.ibl_alf, args.output, args.permutations),
        "buzsaki": validate_buzsaki(
            args.buzsaki_nwb, args.output, args.permutations
        ),
        "validation_parameters": {
            "permutations": args.permutations,
            "warning": (
                "The minimum attainable p value is 1/(permutations+1). "
                "This run validates software integration, not scientific claims."
            ),
        },
    }
    summary = args.output / "validation_summary.json"
    summary.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nSaved: {summary}")


if __name__ == "__main__":
    main()
