"""Point a completed project at its verified, project-owned voltage cache."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from neuroflow.analysis import load_recording
from neuroflow.project import load_project, save_project


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    args = parser.parse_args()
    state = load_project(args.project)
    cache = state.root / "cache" / "sorting_input_selected_channels.bin"
    expected = int(state.duration_seconds * state.sampling_rate) * state.channel_count * np.dtype(state.dtype).itemsize
    if not cache.is_file() or cache.stat().st_size != expected:
        raise RuntimeError(f"Project-owned voltage cache is missing/incomplete: {cache}")
    original = str(state.source_path or state.recording_path or "")
    state.metadata.setdefault("source_provenance", {})["original_recording_directory"] = original
    state.metadata["portable_recording"] = {
        "relative_path": "cache/sorting_input_selected_channels.bin",
        "expected_bytes": expected,
        "channels": state.channel_count,
        "sampling_rate_hz": state.sampling_rate,
        "dtype": state.dtype,
        "note": "Selected subject channels only; original Open Ephys directory not required for saved-project analysis or re-sorting.",
    }
    state.source_path = cache
    state.recording_path = cache
    save_project(state)
    reopened = load_project(args.project)
    raw = load_recording(reopened)
    assert reopened.ready and raw.shape == (int(state.duration_seconds * state.sampling_rate), state.channel_count)
    assert reopened.source_path == cache and reopened.recording_path == cache
    print(json.dumps({
        "project": str(args.project),
        "portable_voltage": str(cache),
        "bytes": expected,
        "shape": list(raw.shape),
        "original_source_recorded": original,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
