from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import neo
import quantities as pq
import pytest
from elephant.spike_train_correlation import spike_time_tiling_coefficient
from neo.rawio.openephysrawio import (
    HEADER_SIZE,
    continuous_dtype,
    events_dtype,
)

from neuroflow.analysis import load_recording, preprocessing_preview, run_raw_qc
from neuroflow.audit import audit_log_path, audited_stage
from neuroflow.data_import import import_device_recording
from neuroflow.ephys_toolkit import _linear_sttc
from neuroflow.medpc import import_medpc_behavior, parse_medpc_file
from neuroflow.models import ProjectState
from neuroflow.project import load_project, save_project
from neuroflow.recording_io import prepare_interleaved_binary
from neuroflow.synchronization import synchronize_existing_events
from neuroflow.sorting import (
    kilosort_runtime_summary,
    load_kilosort4_result,
    load_spikeinterface_result,
)


def _header(**values: object) -> bytes:
    fields = {
        "format": "'Open Ephys Data Format'",
        "version": 0.6,
        "header_bytes": 1024,
        "sampleRate": 30_000,
        "bitVolts": 0.195,
        **values,
    }
    text = "".join(f"header.{key} = {value};" for key, value in fields.items())
    return text.encode("ascii").ljust(HEADER_SIZE, b" ")


def _write_continuous(path: Path, channel: int) -> None:
    records = np.zeros(12, dtype=continuous_dtype)
    records["timestamp"] = 1_000 + np.arange(len(records)) * 1024
    records["nb_sample"] = 1024
    records["rec_num"] = 0
    values = np.arange(len(records) * 1024, dtype=np.int16).reshape(-1, 1024)
    records["samples"] = values + channel * 100
    records["markers"][:, [0, 2, 4, 6, 8]] = np.array(
        [0, 1, 2, 3, 4], dtype=np.uint8
    )
    records["markers"][:, [1, 3, 5, 7, 9]] = 255
    with path.open("wb") as handle:
        handle.write(_header(channel=f"'CH{channel}'"))
        records.tofile(handle)


def _write_events(path: Path) -> None:
    rows = np.zeros(6, dtype=events_dtype)
    rows["timestamp"] = [1_300, 1_330, 4_300, 4_330, 7_300, 7_330]
    rows["event_type"] = 3
    rows["processor_id"] = 100
    rows["event_id"] = [1, 0, 1, 0, 1, 0]
    rows["chan_id"] = 0
    with path.open("wb") as handle:
        handle.write(
            _header(
                channel="'Events'",
                channelType="'Event'",
                description="'digital edges'",
            )
        )
        rows.tofile(handle)


def test_open_ephys_legacy_is_linked_and_read_on_demand(tmp_path: Path):
    source = tmp_path / "Record Node 107"
    source.mkdir()
    _write_continuous(source / "100_RhythmData_CH1.continuous", 1)
    _write_continuous(source / "100_RhythmData_CH2.continuous", 2)
    _write_events(source / "100_RhythmData.events")
    (source / "settings.xml").write_text(
        """
        <SETTINGS><SIGNALCHAIN>
          <PROCESSOR name="Bandpass Filter"><PARAMETERS low_cut="250" high_cut="8000"/></PROCESSOR>
          <PROCESSOR name="Common Avg Ref"><PARAMETERS Reference="1,2"/></PROCESSOR>
        </SIGNALCHAIN></SETTINGS>
        """,
        encoding="utf-8",
    )

    state = import_device_recording(
        tmp_path / "project",
        source,
        "Open Ephys",
        channel_selection="1-2",
    )

    assert state.recording_path == source
    assert not (state.root / "cache" / "normalized_recording.bin").exists()
    assert state.channel_count == 2
    assert state.metadata["digital_event_count"] == 6
    assert state.metadata["acquisition_preprocessing"]["lfp_available"] is False
    raw = load_recording(state)
    assert raw.shape == (12 * 1024, 2)
    assert raw[:3, 0].tolist() == [100, 101, 102]
    assert raw[:3, 1].tolist() == [200, 201, 202]
    qc = run_raw_qc(state, seconds=0.1)
    assert len(qc["channel_rms"]) == 2
    preview = preprocessing_preview(state, start_seconds=0, duration_seconds=0.1)
    assert preview["source_already_preprocessed"] is True
    assert preview["lfp_available"] is False
    state.metadata["interleaved_cache_chunk_bytes"] = 4096
    progress_messages = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        cache = prepare_interleaved_binary(
            state,
            state.root / "cache" / "selected_channels.bin",
            progress_messages.append,
        )
    cached = np.fromfile(cache, dtype=np.int16).reshape(-1, 2)
    assert np.array_equal(cached[:4], raw[:4])
    assert np.array_equal(cached, raw[:])
    assert not [item for item in caught if item.category is ResourceWarning]
    assert "seconds written" in progress_messages[-1]
    assert "chunks" in progress_messages[-1]

    restored = load_project(state.root)
    assert restored.metadata["recording_adapter"]["channel_ids"] == ["1", "2"]
    assert load_recording(restored)[:2].shape == (2, 2)

    restored.metadata["recording_adapter"]["start_frame"] = 10
    restored.metadata["recording_adapter"]["end_frame"] = 20
    sliced = load_recording(restored)
    assert sliced.shape == (10, 2)
    assert sliced[:2, 0].tolist() == [110, 111]


def test_load_recording_prefers_verified_sorting_cache(tmp_path: Path):
    project_root = tmp_path / "linked_project"
    cache_path = (
        project_root / "cache" / "sorting_input_selected_channels.bin"
    )
    cache_path.parent.mkdir(parents=True)
    expected = np.arange(24, dtype=np.int16).reshape(6, 4)
    expected.tofile(cache_path)
    state = ProjectState(
        name="linked",
        root=project_root,
        recording_path=tmp_path / "missing_source",
        sampling_rate=3.0,
        channel_count=4,
        duration_seconds=2.0,
        dtype="int16",
        metadata={"recording_adapter": {"type": "spikeinterface"}},
    )

    observed = load_recording(state)

    assert isinstance(observed, np.memmap)
    np.testing.assert_array_equal(observed, expected)


def test_medpc_event_codes_are_preserved_and_ttl_aligned(tmp_path: Path):
    path = tmp_path / "Example subject"
    path.write_text(
        """
File: C:\\MED-PC\\DATA\\ExampleSubject
Start Date: 07/25/24
Subject: example
Box: 1
MSN: example_box1
C:
     0: 11 1 12 11 2 12 11 3 12
D:
     0: 1.000 1.010 1.020 1.100 1.110 1.120 1.200 1.210 1.220
""".strip(),
        encoding="utf-8",
    )
    parsed = parse_medpc_file(path)
    assert parsed.metadata["Subject"] == "example"
    assert parsed.arrays["C"].astype(int).tolist() == [11, 1, 12, 11, 2, 12, 11, 3, 12]

    state = ProjectState(root=tmp_path / "project")
    state.metadata["digital_events"] = [
        {"channel": 0, "edge": "rising", "time_seconds": value}
        for value in (0.010, 0.110, 0.210)
    ]
    result = import_medpc_behavior(
        state,
        path,
        ttl_channel=0,
        sync_event_code=11,
    )
    assert result["matched_count"] == 3
    assert result["subject"] == "example"
    assert state.events[0]["event_code"] == 11
    assert state.events[0]["event_order"] == 1
    assert "trial" not in state.events[0]
    assert state.trials == []
    assert np.allclose(
        [state.events[index]["time_seconds"] for index in (0, 3, 6)],
        [0.010, 0.110, 0.210],
    )
    assert (
        state.metadata["medpc"]["event_dictionary_status"]
        == "complete_for_observed_codes"
    )
    assert state.events[0]["label"] == "synchronization_on"
    assert state.events[0]["event_semantics_status"] == "confirmed"
    assert state.events[0]["analysis_role"] == "synchronization"
    assert state.events[1]["label"] == "well_head"
    assert state.events[1]["event_semantics_status"] == "confirmed"
    assert state.events[1]["analysis_role"] == "task_event"
    assert state.metadata["trial_definition"]["status"] == "not_defined"
    assert state.metadata["event_inventory"]["by_code"]["11"]["count"] == 3
    retained = synchronize_existing_events(state)
    assert retained["method"] == "piecewise_linear_ttl_anchors"
    assert state.trials == []


def test_legacy_medpc_event_rows_are_not_restored_as_trials(tmp_path: Path):
    state = ProjectState(root=tmp_path / "legacy_medpc")
    state.metadata["behavior_format"] = "MED-PC"
    state.metadata["medpc"] = {"event_codes": [11, 12]}
    state.events = [
        {
            "trial": index + 1,
            "event_index": index,
            "event_code": code,
            "label": f"event_{code}",
            "analysis_role": "synchronization",
            "time_seconds": float(index),
        }
        for index, code in enumerate((11, 12))
    ]
    state.trials = [dict(event) for event in state.events]

    restored = load_project(save_project(state))

    assert restored.trials == []
    assert restored.events[0]["event_order"] == 1
    assert "trial" not in restored.events[0]
    assert restored.metadata["trial_definition"]["status"] == "not_defined"


def test_linear_memory_sttc_matches_elephant_reference():
    first = np.array([0.1, 0.2, 0.5, 0.9])
    second = np.array([0.11, 0.19, 0.7])
    first_train = neo.SpikeTrain(
        first * pq.s,
        t_start=0 * pq.s,
        t_stop=1 * pq.s,
    )
    second_train = neo.SpikeTrain(
        second * pq.s,
        t_start=0 * pq.s,
        t_stop=1 * pq.s,
    )
    expected = spike_time_tiling_coefficient(
        first_train,
        second_train,
        dt=0.02 * pq.s,
    )
    actual = _linear_sttc(
        first,
        second,
        dt_seconds=0.02,
        start_seconds=0.0,
        stop_seconds=1.0,
    )
    assert np.isclose(actual, expected)


def test_existing_kilosort_output_can_be_registered_without_rerun(tmp_path: Path):
    results = tmp_path / "kilosort4"
    results.mkdir()
    np.save(results / "spike_times.npy", np.array([[30], [60], [90], [120]]))
    np.save(results / "spike_clusters.npy", np.array([[0], [1], [0], [1]]))
    (results / "neuroflow_sorting_summary.json").write_text(
        """
        {
          "environment": {
            "kilosort_version": "4.1.7",
            "device_name": "test GPU"
          },
          "settings": {"fs": 30000}
        }
        """,
        encoding="utf-8",
    )
    state = ProjectState(
        root=tmp_path / "project",
        sampling_rate=30_000,
        channel_count=2,
        electrode_type="custom microwire array",
    )
    state.metadata["probe"] = {
        "geometry_mode": "independent_contacts",
        "brain_region": "OFC",
    }

    spikes = load_kilosort4_result(state, results)

    assert np.allclose(spikes[0], [0.001, 0.003])
    assert np.allclose(spikes[1], [0.002, 0.004])
    assert state.active_sorter_key == "kilosort4"
    assert state.sorting_provenance["kilosort4"][
        "recovered_from_existing_output"
    ]
    assert (
        state.sorting_provenance["kilosort4"]["probe_geometry_mode"]
        == "independent_contacts"
    )
    variant = load_kilosort4_result(
        state,
        results,
        sorter_key="kilosort4_th6_5",
    )
    assert np.allclose(variant[0], spikes[0])
    assert set(state.sorting_results) == {"kilosort4", "kilosort4_th6_5"}
    assert state.active_sorter_key == "kilosort4_th6_5"
    assert (
        state.sorting_provenance["kilosort4_th6_5"]["sorter_key"]
        == "kilosort4_th6_5"
    )


def test_existing_spikeinterface_output_can_be_registered_without_rerun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    import spikeinterface as si
    import spikeinterface.sorters as ss

    results = tmp_path / "mountainsort5"
    results.mkdir()
    (results / "spikeinterface_log.json").write_text(
        json.dumps(
            {
                "sorter_name": "mountainsort5",
                "sorter_params": {"detect_threshold": 5.5},
                "error": False,
            }
        ),
        encoding="utf-8",
    )
    sorting = si.NumpySorting.from_unit_dict(
        [{7: np.array([30, 60]), 9: np.array([90])}],
        sampling_frequency=30_000,
    )
    monkeypatch.setattr(ss, "read_sorter_folder", lambda *args, **kwargs: sorting)
    state = ProjectState(
        root=tmp_path / "project",
        sampling_rate=30_000,
        channel_count=2,
    )

    spikes = load_spikeinterface_result(
        state,
        "mountainsort5",
        results,
        update_comparison=False,
    )

    np.testing.assert_allclose(spikes[7], [0.001, 0.002])
    np.testing.assert_allclose(spikes[9], [0.003])
    assert state.active_sorter_key == "mountainsort5"
    assert state.sorting_provenance["mountainsort5"][
        "recovered_from_existing_output"
    ]
    assert state.sorting_provenance["mountainsort5"]["settings"][
        "detect_threshold"
    ] == 5.5


def test_kilosort_runtime_parser_accepts_timestamped_log_lines(tmp_path: Path):
    results = tmp_path / "kilosort4"
    results.mkdir()
    (results / "kilosort4.log").write_text(
        "\n".join(
            [
                "2026-07-28 20:19:40 kilosort.run INFO Total runtime: 382.34s",
                "2026-07-28 20:19:40 kilosort.run INFO preprocessing: 1.2s (0.32) %",
                "2026-07-28 20:19:40 kilosort.run INFO drift corr: 0.0s (0.00) %",
                "2026-07-28 20:19:40 kilosort.run INFO spike det. (univ): 194.0s",
                "2026-07-28 20:19:40 kilosort.run INFO cluster (final): 71.1s",
                "2026-07-28 20:19:40 kilosort.run INFO preprocessing: sys 17.4 GB",
            ]
        ),
        encoding="utf-8",
    )

    summary = kilosort_runtime_summary(results)

    assert summary["total_runtime_seconds"] == 382.34
    assert summary["steps_seconds"]["preprocessing"] == 1.2
    assert summary["steps_seconds"]["drift_correction"] == 0.0
    assert summary["steps_seconds"]["universal_spike_detection"] == 194.0
    assert summary["steps_seconds"]["final_clustering"] == 71.1


def test_structured_stage_audit_records_success_and_failure(tmp_path: Path):
    state = ProjectState(root=tmp_path / "audited", name="Audited project")
    with audited_stage(
        state,
        "raw_qc",
        input_files=[tmp_path / "recording"],
        channel_selection="1-32",
        segment={"start_seconds": 0, "duration_seconds": 1800},
        tool="NeuroFlow",
        tool_version="test",
        parameters={"windows": 12},
    ) as record:
        record["outputs"].append("qc.json")
        warnings.warn("test warning", RuntimeWarning)

    assert state.metadata["structured_run_log"][0]["status"] == "completed"
    assert state.metadata["structured_run_log"][0]["elapsed_seconds"] >= 0
    assert state.metadata["structured_run_log"][0]["warnings"][0][
        "category"
    ] == "RuntimeWarning"

    with pytest.raises(ValueError):
        with audited_stage(state, "failing_stage"):
            raise ValueError("expected failure")

    assert state.metadata["structured_run_log"][1]["status"] == "failed"
    assert state.metadata["structured_run_log"][1]["error"]["type"] == "ValueError"
    lines = audit_log_path(state).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
