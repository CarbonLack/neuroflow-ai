"""Project-local SpikeInterface SortingAnalyzer integration."""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from .models import ProjectState


ANALYZER_EXTENSIONS: tuple[tuple[str, dict[str, Any]], ...] = (
    ("random_spikes", {"max_spikes_per_unit": 1_000, "seed": 0}),
    ("noise_levels", {}),
    ("waveforms", {"ms_before": 1.0, "ms_after": 2.0}),
    ("templates", {}),
    ("spike_amplitudes", {}),
    ("unit_locations", {}),
    ("correlograms", {"window_ms": 100.0, "bin_ms": 1.0}),
    ("template_similarity", {}),
    ("principal_components", {"n_components": 5, "mode": "by_channel_local"}),
    ("quality_metrics", {"skip_pc_metrics": False}),
)


def _recording(state: ProjectState):
    import spikeinterface as si

    adapter = state.metadata.get("recording_adapter", {})
    if adapter.get("type") == "spikeinterface":
        from .recording_io import get_recording_extractor

        recording = get_recording_extractor(state)
    else:
        recording = si.read_binary(
            [state.recording_path], sampling_frequency=state.sampling_rate,
            num_channels=state.channel_count, dtype=state.dtype,
            gain_to_uV=state.scale_uv_per_bit,
        )
    from .sorting import _attach_probe

    return _attach_probe(recording, state)


def _sorting(state: ProjectState):
    import spikeinterface as si

    samples = {
        int(unit_id): np.unique(
            np.rint(np.asarray(times, dtype=float) * state.sampling_rate).astype(np.int64)
        )
        for unit_id, times in state.sorted_spikes.items()
    }
    return si.NumpySorting.from_unit_dict([samples], state.sampling_rate)


def run_sorting_analyzer(
    state: ProjectState,
    *,
    progress: Callable[[str], None] | None = None,
    progress_value: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Compute dependency-aware postprocessing without hiding partial failures."""
    import spikeinterface as si

    sorter_key = state.active_sorter_key or "unassigned"
    output = state.root / "results" / "spikeinterface_analyzer" / sorter_key
    output.parent.mkdir(parents=True, exist_ok=True)
    analyzer = si.create_sorting_analyzer(
        sorting=_sorting(state), recording=_recording(state),
        format="binary_folder", folder=output, sparse=True, overwrite=True,
    )
    completed: list[str] = []
    failures: dict[str, str] = {}
    for index, (name, params) in enumerate(ANALYZER_EXTENSIONS, 1):
        if progress:
            progress(f"SpikeInterface analyzer: {name}")
        if progress_value:
            progress_value(index - 1, len(ANALYZER_EXTENSIONS), name)
        try:
            analyzer.compute(name, **params)
            completed.append(name)
        except Exception as exc:  # noqa: BLE001 - extension isolation is deliberate
            failures[name] = f"{type(exc).__name__}: {exc}"
        if progress_value:
            progress_value(index, len(ANALYZER_EXTENSIONS), name)
    report = {
        "schema": "neuroephys.spikeinterface-analyzer.v1",
        "spikeinterface_version": getattr(si, "__version__", "unknown"),
        "sorter": sorter_key,
        "folder": str(output),
        "extensions_completed": completed,
        "extension_failures": failures,
        "unit_count": len(state.sorted_spikes),
        "source_sorting_unchanged": True,
        "manual_curation_note": (
            "Analyzer extensions support review and export. Human edits remain in the "
            "project curation layer and do not overwrite sorter output."
        ),
    }
    report_path = output.parent / f"{sorter_key}_analyzer_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    state.metadata.setdefault("spikeinterface_analyzers", {})[sorter_key] = report
    state.log(
        f"SpikeInterface analyzer completed {len(completed)}/{len(ANALYZER_EXTENSIONS)} extensions"
    )
    return report
