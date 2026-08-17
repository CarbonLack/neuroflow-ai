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

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
