from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .simulation import generate_demo_recording
from .sorting import kilosort_environment, refresh_sorter_catalog, run_sorter


def run_packaged_ai_self_test(workspace: Path) -> int:
    """Verify the packaged privacy summary and structured response path offline."""
    workspace.mkdir(parents=True, exist_ok=True)
    report_path = workspace / "packaged_ai_self_test.json"
    try:
        from .ai import AISettings, build_project_summary, normalize_ai_response

        project_root = workspace / "self_test" / "ai"
        state = generate_demo_recording(
            project_root,
            duration_seconds=2,
            channel_count=4,
            sampling_rate=30_000,
        )
        summary = build_project_summary(state, "qc")
        serialized = json.dumps(summary, ensure_ascii=False)
        if str(project_root) in serialized or "raw_path" in serialized:
            raise RuntimeError("AI privacy summary exposed a local project path")
        response = normalize_ai_response(
            {
                "answer": "Inspect raw QC evidence before preprocessing.",
                "warnings": [],
                "plan": [
                    {
                        "stage": "qc",
                        "reason": "Establish signal quality.",
                        "prerequisites": ["Imported recording"],
                        "recommended_parameters": [],
                    }
                ],
                "suggested_next_stage": "qc",
                "requires_user_confirmation": True,
            },
            settings=AISettings(model="offline-self-test"),
        )
        report = {
            "ok": True,
            "summary_keys": sorted(summary),
            "suggested_next_stage": response.suggested_next_stage,
            "requires_user_confirmation": response.requires_user_confirmation,
            "network_request_made": False,
        }
    except Exception as exc:  # noqa: BLE001 - persist the complete packaged failure
        report = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0 if report["ok"] else 1


def run_packaged_figure_export_self_test(workspace: Path) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    report_path = workspace / "packaged_figure_export_self_test.json"
    output_dir = workspace / "self_test" / "figure_export"
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        from matplotlib.figure import Figure

        figure = Figure(figsize=(4, 3))
        axis = figure.subplots()
        axis.plot([0, 1, 2], [0, 1, 0], color="#1f7a63")
        axis.set(xlabel="Time (s)", ylabel="Value", title="NeuroEphys AI export test")
        outputs = []
        for suffix in ("svg", "pdf", "png"):
            path = output_dir / f"export_test.{suffix}"
            figure.savefig(path, dpi=150)
            if not path.is_file() or path.stat().st_size < 100:
                raise RuntimeError(f"Figure export did not create a valid {suffix} file")
            outputs.append(str(path))
        report = {"ok": True, "outputs": outputs}
    except Exception as exc:  # noqa: BLE001 - self-test persists the full failure
        report = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0 if report["ok"] else 1


def run_packaged_kilosort_self_test(workspace: Path) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    log_path = workspace / "packaged_kilosort_self_test.log"
    report_path = workspace / "packaged_kilosort_self_test.json"
    with log_path.open("w", encoding="utf-8", buffering=1) as stream:
        sys.stdout = stream
        sys.stderr = stream
        try:
            stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
            project_root = workspace / "self_test" / stamp
            state = generate_demo_recording(
                project_root,
                duration_seconds=8,
                channel_count=8,
                sampling_rate=30_000,
            )
            spikes = run_sorter(
                state,
                "kilosort4",
                project_root / "results" / "kilosort4",
                print,
                settings={
                    "batch_size": 120_000,
                    "nblocks": 0,
                    "Th_universal": 9,
                    "Th_learned": 8,
                    "save_extra_vars": True,
                },
            )
            report = {
                "ok": True,
                "environment": kilosort_environment(),
                "project": str(project_root),
                "units": len(spikes),
                "spikes": sum(len(value) for value in spikes.values()),
                "diagnostic_files": state.metadata["sorting"]["diagnostic_files"],
            }
        except Exception as exc:  # noqa: BLE001 - self-test must persist full failure
            report = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0 if report["ok"] else 1


def run_packaged_mountainsort_self_test(workspace: Path) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    log_path = workspace / "packaged_mountainsort_self_test.log"
    report_path = workspace / "packaged_mountainsort_self_test.json"
    with log_path.open("w", encoding="utf-8", buffering=1) as stream:
        sys.stdout = stream
        sys.stderr = stream
        try:
            stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
            project_root = workspace / "self_test" / f"{stamp}_mountainsort5"
            state = generate_demo_recording(
                project_root,
                duration_seconds=6,
                channel_count=8,
                sampling_rate=30_000,
            )
            spikes = run_sorter(
                state,
                "mountainsort5",
                project_root / "results" / "mountainsort5",
                print,
                settings={
                    "scheme": "1",
                    "detect_threshold": 5.0,
                },
            )
            catalog = {
                item["key"]: item for item in refresh_sorter_catalog()
            }
            sorter = catalog["mountainsort5"]
            comparison = state.sorting_comparison
            report = {
                "ok": True,
                "environment": {
                    "available": sorter["installed"],
                    "version": sorter["version"],
                    "backend": sorter["backend"],
                },
                "project": str(project_root),
                "units": len(spikes),
                "spikes": sum(len(value) for value in spikes.values()),
                "schema": state.sorting_provenance["mountainsort5"]["schema"],
                "time_unit": state.sorting_provenance["mountainsort5"]["time_unit"],
                "comparison_mode": comparison.get("mode"),
            }
        except Exception as exc:  # noqa: BLE001 - self-test must persist full failure
            report = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0 if report["ok"] else 1


def run_packaged_internal_sorters_self_test(workspace: Path) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    log_path = workspace / "packaged_internal_sorters_self_test.log"
    report_path = workspace / "packaged_internal_sorters_self_test.json"
    report: dict = {"ok": False, "sorters": {}}
    with log_path.open("w", encoding="utf-8", buffering=1) as stream:
        sys.stdout = stream
        sys.stderr = stream
        try:
            stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
            project_root = workspace / "self_test" / f"{stamp}_internal_sorters"
            state = generate_demo_recording(
                project_root,
                duration_seconds=6,
                channel_count=8,
                sampling_rate=30_000,
            )
            for sorter_key in (
                "spykingcircus2",
                "tridesclous2",
                "simple",
                "lupin",
            ):
                try:
                    spikes = run_sorter(
                        state,
                        sorter_key,
                        project_root / "results" / sorter_key,
                        print,
                    )
                    report["sorters"][sorter_key] = {
                        "ok": True,
                        "units": len(spikes),
                        "spikes": sum(len(value) for value in spikes.values()),
                        "schema": state.sorting_provenance[sorter_key]["schema"],
                    }
                except Exception as exc:  # noqa: BLE001 - continue the matrix
                    report["sorters"][sorter_key] = {
                        "ok": False,
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                    }
            report["ok"] = all(
                value["ok"] for value in report["sorters"].values()
            )
            report["comparison_sorters"] = sorted(
                state.sorting_comparison.get("sorters", {})
            )
        except Exception as exc:  # noqa: BLE001 - persist setup failure
            report = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "sorters": report.get("sorters", {}),
            }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0 if report["ok"] else 1
