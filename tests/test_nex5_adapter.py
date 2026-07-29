from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from neuroflow.analysis import compute_unit_metrics
from neuroflow.models import ProjectState
from neuroflow.nex5_adapter import (
    import_nex5_sorting_into_project,
    inspect_nex5_source,
)
from neuroflow.project import load_project
from neuroflow.sorting_results import (
    compare_sorting_pair_with_lag,
    register_sorting_result,
)

nex5file = pytest.importorskip("nex5file")


def _write_nex5(path: Path) -> None:
    from nex5file.filedata import FileData
    from nex5file.writer import Writer

    data = FileData(tsFrequency=30_000)
    data.AddEvent("recording_end", [12.0])
    timestamps = [2.1, 2.2, 2.3]
    waveforms = [
        [-5.0, -20.0, -45.0, -15.0],
        [-4.0, -22.0, -43.0, -16.0],
        [-6.0, -21.0, -44.0, -14.0],
    ]
    data.AddNeuron("CH12a", timestamps, wire=12, unit=1)
    data.AddWaveVarWithFloats(
        "CH12a_wf",
        30_000,
        timestamps,
        waveforms,
    )
    Writer().WriteNex5File(data, str(path))


def test_nex5_result_import_preserves_units_and_waveforms(tmp_path: Path):
    source = tmp_path / "offline"
    source.mkdir()
    nex5_path = source / "example_SW#1_LO.nex5"
    _write_nex5(nex5_path)
    inspected = inspect_nex5_source(source, filename_filter="SW#1")
    assert inspected["file_count"] == 1
    assert inspected["unit_count"] == 1
    state = ProjectState(
        root=tmp_path / "project",
        sampling_rate=30_000,
        duration_seconds=10.0,
        channel_count=32,
    )

    summary = import_nex5_sorting_into_project(
        state,
        source,
        filename_filter="SW#1",
        alignment_mode="manual",
        manual_offset_seconds=2.0,
    )

    np.testing.assert_allclose(
        state.sorting_results["offline_sorter_nex5"][0],
        [0.1, 0.2, 0.3],
    )
    assert summary["unit_count"] == 1
    assert summary["files"][0]["units"][0]["channel_number"] == 12
    assert (
        state.sorting_provenance["offline_sorter_nex5"]["unit_metadata"]["0"][
            "source_variable"
        ]
        == "CH12a"
    )
    waveform_archive = Path(summary["waveform_summaries"])
    with np.load(waveform_archive) as archive:
        assert archive["unit_0_mean"].shape == (4,)
    restored = load_project(state.root)
    np.testing.assert_allclose(
        restored.sorting_results["offline_sorter_nex5"][0],
        [0.1, 0.2, 0.3],
    )


def test_nex5_auto_alignment_rejects_recording_segments(tmp_path: Path):
    source = tmp_path / "example_SW#1_LO.nex5"
    _write_nex5(source)
    state = ProjectState(
        root=tmp_path / "segment_project",
        sampling_rate=30_000,
        duration_seconds=5.0,
    )
    state.metadata["recording_adapter"] = {
        "frame_count": 300_000,
        "start_frame": 0,
        "end_frame": 150_000,
    }

    with pytest.raises(ValueError, match="recording segment"):
        import_nex5_sorting_into_project(
            state,
            source,
            alignment_mode="auto_project_duration",
        )


def test_lag_aware_sorting_comparison_exports_tables_and_figures(
    tmp_path: Path,
):
    state = ProjectState(
        root=tmp_path / "comparison",
        sampling_rate=30_000,
        duration_seconds=1.0,
    )
    reference = np.array([0.1, 0.2, 0.3, 0.4])
    tested = reference + 0.0003
    register_sorting_result(
        state,
        "external",
        {4: reference},
        {
            "unit_metadata": {
                "4": {
                    "source_variable": "CH12a",
                    "channel_number": 12,
                }
            }
        },
    )
    register_sorting_result(
        state,
        "kilosort4",
        {7: tested},
        {},
    )

    summary = compare_sorting_pair_with_lag(
        state,
        "external",
        "kilosort4",
    )

    assigned = summary["one_to_one_assignment"][0]
    assert assigned["matched_spikes"] == 4
    assert assigned["f1"] == pytest.approx(1.0)
    assert abs(assigned["estimated_lag_ms"] - 0.3) <= 0.06
    for path in summary["outputs"].values():
        assert Path(path).exists()


def test_unit_qc_flags_cross_unit_timestamp_overlap_without_deleting_units(
    tmp_path: Path,
):
    state = ProjectState(
        root=tmp_path / "duplicate_screen",
        duration_seconds=1.0,
        sampling_rate=30_000,
    )
    register_sorting_result(
        state,
        "external",
        {
            1: np.array([0.1, 0.2, 0.3, 0.4]),
            2: np.array([0.1, 0.2, 0.7, 0.8]),
        },
        {},
    )

    metrics = compute_unit_metrics(state)

    assert set(state.sorted_spikes) == {1, 2}
    assert metrics[0]["max_cross_unit_overlap_fraction"] == pytest.approx(0.5)
    assert metrics[0]["duplicate_partner_unit"] == 2
    screen = state.metadata["unit_qc_duplicate_screen"]["external"]
    assert screen["flagged_pairs"][0]["matched_spike_count"] == 2
