from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from neuroflow.analysis import compute_unit_metrics  # noqa: E402
from neuroflow.audit import audited_stage  # noqa: E402
from neuroflow.nex5_adapter import (  # noqa: E402
    import_nex5_sorting_into_project,
    inspect_nex5_source,
)
from neuroflow.project import load_project, save_project  # noqa: E402
from neuroflow.sorting_results import (  # noqa: E402
    activate_sorting_result,
    compare_sorting_pair_with_lag,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attach an Offline Sorter/NeuroExplorer NEX5 result to an existing "
            "NeuroEphys AI project and compare it with a saved sorter output."
        )
    )
    parser.add_argument("project", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("--filename-filter")
    parser.add_argument(
        "--result-key",
        default="offline_sorter_nex5",
    )
    parser.add_argument(
        "--tested-key",
        default="kilosort4",
    )
    parser.add_argument(
        "--alignment",
        choices=("auto_project_duration", "preserve", "manual"),
        default="auto_project_duration",
    )
    parser.add_argument("--manual-offset-seconds", type=float, default=0.0)
    parser.add_argument("--tolerance-ms", type=float, default=0.5)
    parser.add_argument("--lag-search-ms", type=float, default=2.0)
    parser.add_argument(
        "--compute-unit-qc",
        action="store_true",
    )
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    state = load_project(arguments.project)
    original_active = state.active_sorter_key
    inspected = inspect_nex5_source(
        arguments.source,
        filename_filter=arguments.filename_filter,
    )
    started = time.perf_counter()
    imported = import_nex5_sorting_into_project(
        state,
        arguments.source,
        sorter_key=arguments.result_key,
        filename_filter=arguments.filename_filter,
        alignment_mode=arguments.alignment,
        manual_offset_seconds=arguments.manual_offset_seconds,
        activate=False,
    )
    with audited_stage(
        state,
        "external_sorting_comparison",
        input_files=[
            Path(item["path"]) for item in inspected["files"]
        ],
        channel_selection=state.metadata.get("selected_channel_ids", []),
        segment={
            "start_seconds": 0.0,
            "duration_seconds": float(state.duration_seconds),
        },
        tool="NeuroEphys AI lag-aware sorter comparison",
        parameters={
            "reference_key": arguments.result_key,
            "tested_key": arguments.tested_key,
            "tolerance_ms": arguments.tolerance_ms,
            "lag_search_ms": arguments.lag_search_ms,
            "reference_is_ground_truth": False,
        },
    ) as audit:
        comparison = compare_sorting_pair_with_lag(
            state,
            arguments.result_key,
            arguments.tested_key,
            tolerance_ms=arguments.tolerance_ms,
            lag_search_ms=arguments.lag_search_ms,
        )
        audit["outputs"] = list(comparison["outputs"].values())

    metrics = []
    duplicate_screen = {}
    if arguments.compute_unit_qc:
        with audited_stage(
            state,
            "external_sorting_unit_qc",
            input_files=[
                Path(item["path"]) for item in inspected["files"]
            ],
            channel_selection=state.metadata.get(
                "selected_channel_ids",
                [],
            ),
            segment={
                "start_seconds": 0.0,
                "duration_seconds": float(state.duration_seconds),
            },
            tool="NeuroEphys AI Unit QC",
            parameters={
                "sorter_key": arguments.result_key,
                "source_result_read_only": True,
            },
        ):
            activate_sorting_result(state, arguments.result_key)
            metrics = compute_unit_metrics(state)
            duplicate_screen = state.metadata.get(
                "unit_qc_duplicate_screen",
                {},
            ).get(arguments.result_key, {})
    if original_active in state.sorting_results:
        activate_sorting_result(state, str(original_active))
    elapsed = time.perf_counter() - started
    report = {
        "schema": "neuroephys.external-sorting-validation.v1",
        "project": str(arguments.project),
        "source": str(arguments.source),
        "source_inspection": inspected,
        "import": imported,
        "comparison": comparison,
        "unit_qc": metrics,
        "duplicate_screen": duplicate_screen,
        "elapsed_seconds": elapsed,
        "active_sorter_restored": state.active_sorter_key,
        "scientific_status": (
            "Technical comparison only. Neither output is ground truth; "
            "candidate units require manual curation."
        ),
    }
    output_dir = Path(comparison["outputs"]["summary_json"]).parent
    report_path = output_dir / "external_sorting_validation_run.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    state.metadata.setdefault("external_sorting_validations", {})[
        f"{arguments.result_key}_vs_{arguments.tested_key}"
    ] = {
        "report": str(report_path),
        "elapsed_seconds": elapsed,
        "reference_is_ground_truth": False,
    }
    state.log(
        f"External sorting validation saved: {report_path}; "
        f"elapsed {elapsed:.2f} s"
    )
    save_project(state)
    print(
        json.dumps(
            {
                "report": str(report_path),
                "reference_units": comparison["reference_unit_count"],
                "tested_units": comparison["tested_unit_count"],
                "strong_matches": comparison["strong_match_count"],
                "elapsed_seconds": elapsed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
