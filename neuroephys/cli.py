from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Sequence

from neuroflow.paths import default_workspace, initialize_workspace
from neuroflow.product import PRODUCT_NAME, PRODUCT_VERSION


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def environment_info(include_sorters: bool = False) -> dict:
    """Return a machine-readable summary of the active Python installation."""

    payload = {
        "application": PRODUCT_NAME,
        "version": PRODUCT_VERSION,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "workspace": str(default_workspace()),
        "packages": {
            name: _package_version(name)
            for name in (
                "neuroephys-ai",
                "numpy",
                "scipy",
                "spikeinterface",
                "PySide6",
                "mountainsort5",
                "kilosort",
            )
        },
    }
    if include_sorters:
        from neuroflow.sorting import refresh_sorter_catalog

        payload["sorters"] = refresh_sorter_catalog()
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neuroephys",
        description="NeuroEphys AI electrophysiology analysis toolkit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {PRODUCT_VERSION}",
    )
    commands = parser.add_subparsers(dest="command")

    info = commands.add_parser("info", help="show installation information")
    info.add_argument("--sorters", action="store_true", help="probe supported sorters")
    info.add_argument("--json", action="store_true", help="emit JSON")

    demo = commands.add_parser("demo", help="create a deterministic teaching project")
    demo.add_argument("output", type=Path, help="new project directory")
    demo.add_argument("--duration", type=float, default=10.0, help="seconds")
    demo.add_argument("--channels", type=int, default=8, help="channel count")
    demo.add_argument("--seed", type=int, default=20260724)

    self_test = commands.add_parser("self-test", help="run an offline package self-test")
    self_test.add_argument(
        "kind",
        choices=("ai", "figures"),
        nargs="?",
        default="ai",
    )
    self_test.add_argument("--workspace", type=Path)

    app = commands.add_parser("app", help="launch the optional desktop interface")
    app.add_argument("--workspace", type=Path)

    population = commands.add_parser(
        "population",
        help="run event-aligned single-trial population analysis",
    )
    population.add_argument("project", type=Path)
    population.add_argument("--event-label")
    population.add_argument("--region")
    population.add_argument("--window-start", type=float, default=-0.5)
    population.add_argument("--window-stop", type=float, default=1.0)
    population.add_argument("--bin-ms", type=float, default=1.0)
    population.add_argument("--sigma-ms", type=float, default=25.0)
    population.add_argument(
        "--baseline-mode",
        choices=("none", "subtract", "zscore"),
        default="none",
    )
    population.add_argument(
        "--baseline-scope",
        choices=("pooled_units", "per_trial"),
        default="pooled_units",
    )
    population.add_argument("--baseline-start", type=float, default=-0.5)
    population.add_argument("--baseline-stop", type=float, default=0.0)
    population.add_argument(
        "--ordering",
        choices=("peak_time", "pca_loading", "rastermap"),
        default="peak_time",
    )
    population.add_argument("--json", action="store_true")

    connectivity = commands.add_parser(
        "connectivity",
        help="run selectable jitter-corrected fine-timing analysis",
    )
    connectivity.add_argument("project", type=Path)
    connectivity.add_argument(
        "--pair-mode",
        choices=("all", "within_region", "between_regions"),
        default="all",
    )
    connectivity.add_argument(
        "--pair-selection",
        choices=("random", "distance", "unit_id"),
        default="random",
    )
    connectivity.add_argument("--max-pairs", type=int, default=500)
    connectivity.add_argument("--min-rate-hz", type=float, default=1.0)
    connectivity.add_argument("--max-distance-um", type=float)
    connectivity.add_argument("--bin-ms", type=float, default=1.0)
    connectivity.add_argument("--max-lag-ms", type=float, default=50.0)
    connectivity.add_argument("--jitter-ms", type=float, default=25.0)
    connectivity.add_argument("--iterations", type=int, default=100)
    connectivity.add_argument(
        "--jitter-strategy",
        choices=("interval", "centered"),
        default="interval",
    )
    connectivity.add_argument(
        "--normalization",
        choices=("counts", "reference_rate", "trial_rate"),
        default="counts",
    )
    connectivity.add_argument(
        "--significance",
        choices=("flank_sd", "jitter_percentile"),
        default="flank_sd",
    )
    connectivity.add_argument("--central-window-ms", type=float, default=10.0)
    connectivity.add_argument("--threshold-sd", type=float, default=7.0)
    connectivity.add_argument("--alpha", type=float, default=0.05)
    connectivity.add_argument(
        "--multiple-comparison",
        choices=("none", "fdr_bh", "bonferroni"),
        default="fdr_bh",
    )
    connectivity.add_argument(
        "--interval-set",
        default="whole_session",
        help="whole_session or a named explicit project interval set",
    )
    connectivity.add_argument("--seed", type=int, default=20260817)
    connectivity.add_argument("--json", action="store_true")
    return parser


def _print_info(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"{payload['application']} {payload['version']}")
    print(f"Python: {payload['python']}")
    print(f"Platform: {payload['platform']}")
    print(f"Workspace: {payload['workspace']}")
    for name, version in payload["packages"].items():
        print(f"{name}: {version or 'not installed'}")
    for sorter in payload.get("sorters", []):
        status = "available" if sorter["installed"] else "unavailable"
        print(f"{sorter['name']}: {status} ({sorter['version']})")


def _event_label(row: dict) -> str:
    return str(row.get("condition", row.get("event", row.get("code", "all"))))


def _run_population_command(args, parser: argparse.ArgumentParser) -> int:
    from neuroflow.population import run_population_dynamics_suite
    from neuroflow.project import load_project, save_project

    state = load_project(args.project.resolve())
    selected_events = [
        row
        for row in state.events
        if args.event_label is None or _event_label(row) == args.event_label
    ]
    if not selected_events:
        parser.error("No project events match --event-label")
    unit_ids = sorted(state.sorted_spikes)
    if args.region is not None:
        regions = {
            int(unit_id): str(region)
            for unit_id, region in state.metadata.get("unit_regions", {}).items()
        }
        unit_ids = [unit_id for unit_id in unit_ids if regions.get(unit_id) == args.region]
    if not unit_ids:
        parser.error("No project units match --region")
    if args.window_stop <= args.window_start or args.bin_ms <= 0 or args.sigma_ms < 0:
        parser.error("Window, bin, and smoothing parameters are invalid")
    baseline_window = None
    if args.baseline_mode != "none":
        if not (
            args.window_start <= args.baseline_start < args.baseline_stop <= args.window_stop
        ):
            parser.error("The baseline must be non-empty and inside the analysis window")
        baseline_window = (args.baseline_start, args.baseline_stop)
    result = run_population_dynamics_suite(
        state,
        event_times_seconds=[float(row["time_seconds"]) for row in selected_events],
        event_labels=[_event_label(row) for row in selected_events],
        unit_ids=unit_ids,
        window_seconds=(args.window_start, args.window_stop),
        bin_size_seconds=args.bin_ms / 1_000,
        smoothing_sigma_seconds=args.sigma_ms / 1_000,
        baseline_window_seconds=baseline_window,
        baseline_mode=args.baseline_mode,
        baseline_scope=args.baseline_scope,
        ordering_method=args.ordering,
    )
    save_project(state)
    payload = {
        "project": str(state.root),
        "trial_count": len(result["event_times_seconds"]),
        "unit_count": len(result["unit_ids"]),
        "time_bin_count": len(result["time_seconds"]),
        "ordering": result["ordering"]["method"],
        "saved": True,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"Population analysis saved: {payload['trial_count']} trials, "
            f"{payload['unit_count']} units, {payload['time_bin_count']} bins"
        )
    return 0


def _run_connectivity_command(args, parser: argparse.ArgumentParser) -> int:
    from neuroflow.connectivity import project_interval_sets, run_connectivity_suite
    from neuroflow.project import load_project, save_project

    state = load_project(args.project.resolve())
    interval_sets = project_interval_sets(state)
    if args.interval_set == "whole_session":
        intervals = None
    elif args.interval_set in interval_sets:
        intervals = interval_sets[args.interval_set]
    else:
        parser.error(
            "Unknown --interval-set. Available: whole_session"
            + (", " + ", ".join(sorted(interval_sets)) if interval_sets else "")
        )
    if (
        args.max_pairs < 1
        or args.bin_ms <= 0
        or args.max_lag_ms <= args.central_window_ms
        or args.jitter_ms <= args.bin_ms
        or args.iterations < 2
        or not 0 < args.alpha < 1
    ):
        parser.error("Connectivity timing, count, or alpha parameters are invalid")
    result = run_connectivity_suite(
        state,
        pair_mode=args.pair_mode,
        pair_selection=args.pair_selection,
        max_pairs=args.max_pairs,
        min_rate_hz=args.min_rate_hz,
        max_distance_um=args.max_distance_um,
        bin_size_seconds=args.bin_ms / 1_000,
        max_lag_seconds=args.max_lag_ms / 1_000,
        jitter_window_seconds=args.jitter_ms / 1_000,
        jitter_iterations=args.iterations,
        jitter_strategy=args.jitter_strategy,
        trial_intervals=intervals,
        interval_label=args.interval_set,
        normalization=args.normalization,
        significance_method=args.significance,
        central_window_seconds=args.central_window_ms / 1_000,
        threshold_sd=args.threshold_sd,
        alpha=args.alpha,
        multiple_comparison=args.multiple_comparison,
        seed=args.seed,
    )
    save_project(state)
    payload = {
        "project": str(state.root),
        "eligible_unit_count": result["eligible_unit_count"],
        "candidate_pair_count": result["candidate_pair_count"],
        "tested_pair_count": result["tested_pair_count"],
        "significant_pair_count": result["significant_pair_count"],
        "pair_selection_truncated": result["pair_selection_truncated"],
        "saved": True,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"Connectivity analysis saved: {payload['tested_pair_count']} tested, "
            f"{payload['significant_pair_count']} significant pairs"
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "info":
        _print_info(environment_info(args.sorters), args.json)
        return 0
    if args.command == "demo":
        if args.duration <= 0 or args.channels <= 0:
            parser.error("--duration and --channels must be greater than zero")
        from neuroflow.data_import import create_simulated_project

        state = create_simulated_project(
            args.output.resolve(),
            duration_seconds=args.duration,
            channel_count=args.channels,
            seed=args.seed,
        )
        print(state.root / "neuroflow_project.json")
        return 0
    if args.command == "self-test":
        from neuroflow.self_test import (
            run_packaged_ai_self_test,
            run_packaged_figure_export_self_test,
        )

        root = initialize_workspace(args.workspace or default_workspace())
        if args.kind == "figures":
            return run_packaged_figure_export_self_test(root)
        return run_packaged_ai_self_test(root)
    if args.command == "app":
        from .app import launch

        return launch(args.workspace)
    if args.command == "population":
        return _run_population_command(args, parser)
    if args.command == "connectivity":
        return _run_connectivity_command(args, parser)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
