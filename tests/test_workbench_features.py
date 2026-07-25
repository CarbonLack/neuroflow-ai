from pathlib import Path

import numpy as np
import spikeinterface.sorters as ss

from neuroflow.analysis import (
    compute_unit_metrics,
    event_aligned_analysis,
)
from neuroflow.data_import import create_simulated_project
from neuroflow.decoding import MODELS, REGRESSION_MODELS, run_regression_suite
from neuroflow.figures import (
    raw_overview_figure,
    sorting_diagnostics_figure,
    statistics_figure,
)
from neuroflow.help_content import CONTROL_HELP, page_controls
from neuroflow.i18n import step_text, tr
from neuroflow.models import ProjectState
from neuroflow.simulation import load_or_generate_demo
from neuroflow.sorting import refresh_sorter_catalog
from neuroflow.statistics import run_statistical_suite
from neuroflow.tutorials import TUTORIALS, tutorial_value


def test_sorter_probe_is_allow_listed(monkeypatch):
    def unrelated_global_probe():
        raise UnicodeDecodeError("utf-8", b"\xb2", 0, 1, "invalid start byte")

    monkeypatch.setattr(ss, "installed_sorters", unrelated_global_probe)
    catalog = refresh_sorter_catalog()
    assert {item["key"] for item in catalog} == {
        "kilosort4",
        "mountainsort5",
        "spykingcircus2",
        "tridesclous2",
        "simple",
        "lupin",
    }
    assert any(item["installed"] for item in catalog)


def test_bilingual_help_covers_every_workflow_step():
    tutorial_keys = {chapter["key"] for chapter in TUTORIALS}
    assert len(tutorial_keys) == 11
    assert tr("run_all", "en_US") == "Run full workflow"
    assert step_text("sorting", "en_US")[0].startswith("04")
    for chapter in TUTORIALS:
        assert tutorial_value(chapter, "title", "zh_CN")
        assert tutorial_value(chapter, "title", "en_US")
        assert tutorial_value(chapter, "checks", "en_US")
        assert page_controls(chapter["key"], "zh_CN")
        assert page_controls(chapter["key"], "en_US")
    for help_item in CONTROL_HELP.values():
        assert help_item["zh_CN"][0] and help_item["zh_CN"][1]
        assert help_item["en_US"][0] and help_item["en_US"][1]


def test_statistics_views_and_model_catalog(tmp_path: Path):
    state = create_simulated_project(
        tmp_path / "project",
        electrode_type="Tetrode array (4 x 4)",
        duration_seconds=10,
        sampling_rate=10_000,
        channel_count=16,
    )
    state.sorted_spikes = state.ground_truth
    compute_unit_metrics(state)
    event_aligned_analysis(state)
    result = run_statistical_suite(state)
    assert len(result["available_tests"]) >= 15
    assert {"effects", "conditions", "diagnostics"} == {
        view
        for view in ("effects", "conditions", "diagnostics")
        if len(statistics_figure(state, view).axes) >= 2
    }
    assert len(MODELS) >= 10
    assert "XGBoost" in MODELS
    regression = run_regression_suite(state, n_splits=3)
    assert len(REGRESSION_MODELS) >= 5
    assert regression["target"] == "reaction_time_seconds"
    assert regression["n_trials"] >= 6


def test_demo_dataset_exposes_exact_import_contract(tmp_path: Path):
    state = load_or_generate_demo(tmp_path / "DemoData" / "NeuroFlow_demo")
    assert state.recording_path.is_file()
    assert (state.root / "README_DATASET.md").is_file()
    assert (state.root / "raw" / "import_config.json").is_file()
    assert (state.root / "raw" / "events.csv").is_file()


def test_sorting_diagnostics_read_real_output_shapes(tmp_path: Path):
    root = tmp_path / "sorting"
    root.mkdir()
    spike_times = np.arange(60) * 100
    clusters = np.repeat(np.arange(3), 20)
    np.save(root / "spike_times.npy", spike_times)
    np.save(root / "spike_clusters.npy", clusters)
    np.save(root / "spike_positions.npy", np.column_stack((clusters, clusters * 20)))
    np.save(root / "amplitudes.npy", np.linspace(1, 3, 60))
    np.save(root / "templates.npy", np.ones((3, 61, 4)))
    np.save(
        root / "channel_positions.npy",
        np.column_stack((np.zeros(4), np.arange(4) * 20)),
    )
    np.save(root / "similar_templates.npy", np.eye(3))
    state = ProjectState(root=tmp_path, sampling_rate=30_000, channel_count=4)
    state.sorted_spikes = {
        index: spike_times[clusters == index] / 30_000 for index in range(3)
    }
    state.metadata["sorting"] = {
        "sorter": "Kilosort4",
        "result_directory": str(root),
        "settings": {"batch_size": 60_000, "nblocks": 0},
    }
    for view in ("pipeline", "drift", "amplitudes", "templates", "similarity", "files"):
        assert sorting_diagnostics_figure(state, view).axes


def test_english_raw_figure_contains_no_chinese_labels(tmp_path: Path):
    state = load_or_generate_demo(tmp_path / "demo")
    state.metadata["language"] = "en_US"
    figure = raw_overview_figure(state, start_seconds=0, visible_channels=4)
    visible_text = " ".join(
        [
            axis.get_title()
            + axis.get_xlabel()
            + axis.get_ylabel()
            + " ".join(label.get_text() for label in axis.get_xticklabels())
            + " ".join(label.get_text() for label in axis.get_yticklabels())
            for axis in figure.axes
        ]
    )
    assert not any("\u4e00" <= character <= "\u9fff" for character in visible_text)
