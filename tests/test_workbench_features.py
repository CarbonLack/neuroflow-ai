from pathlib import Path

import spikeinterface.sorters as ss

from neuroflow.analysis import (
    compute_unit_metrics,
    event_aligned_analysis,
)
from neuroflow.data_import import create_simulated_project
from neuroflow.decoding import MODELS, REGRESSION_MODELS, run_regression_suite
from neuroflow.figures import statistics_figure
from neuroflow.i18n import step_text, tr
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
