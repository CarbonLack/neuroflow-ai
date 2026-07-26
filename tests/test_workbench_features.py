import json
from pathlib import Path

import numpy as np
import spikeinterface.sorters as ss

from neuroflow.analysis import (
    compute_unit_metrics,
    event_aligned_analysis,
    export_reproducible_bundle,
)
from neuroflow.data_import import create_simulated_project
from neuroflow.decoding import MODELS, REGRESSION_MODELS, run_regression_suite
from neuroflow.ephys_toolkit import (
    METHOD_CATALOG,
    provider_status,
    run_lfp_suite,
    run_respiration_case,
    run_spike_field_suite,
    run_spike_train_suite,
)
from neuroflow.figures import (
    raw_overview_figure,
    sorting_diagnostics_figure,
    statistics_figure,
)
from neuroflow.help_content import CONTROL_HELP, page_controls
from neuroflow.i18n import step_text, tr
from neuroflow.models import ProjectState
from neuroflow.project import load_project, save_project
from neuroflow.self_test import run_packaged_figure_export_self_test
from neuroflow.simulation import (
    demo_profile_catalog,
    generate_demo_recording,
    load_or_generate_demo,
)
from neuroflow.sorting import refresh_sorter_catalog
from neuroflow.sorting_results import (
    activate_sorting_result,
    compare_sorting_results,
    register_sorting_result,
)
from neuroflow.statistics import run_statistical_suite
from neuroflow.synchronization import synchronize_existing_events
from neuroflow.tutorial_details import TUTORIAL_DETAILS, localized, localized_rows
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


def test_detailed_tutorials_cover_operations_parameters_and_both_languages():
    assert set(TUTORIAL_DETAILS) == {
        "import",
        "qc",
        "preprocess",
        "sorting",
        "unit_qc",
        "sync",
        "behavior",
        "analysis",
        "statistics",
        "decoding",
        "export",
    }
    for details in TUTORIAL_DETAILS.values():
        for language in ("zh_CN", "en_US"):
            assert localized(details, "narrative", language)
            assert localized(details, "before", language)
            assert localized(details, "recommended", language)
            assert localized(details, "pitfalls", language)
            assert localized(details, "next", language)
            assert localized_rows(details, "operations", language)
            assert localized_rows(details, "parameters", language)
        english_parameters = localized_rows(details, "parameters", "en_US")
        for parameter in english_parameters:
            visible = f"{parameter['name']} {parameter['default']} {parameter['effect']}"
            assert not any("\u4e00" <= char <= "\u9fff" for char in visible)


def test_generated_documentation_is_complete_and_english_is_monolingual():
    site = Path(__file__).resolve().parents[1] / "docs" / "site"
    expected = {
        "index.html",
        "installation.html",
        "gui-guide.html",
        "tutorials.html",
        "data-inputs.html",
        "sorting.html",
        "parameters.html",
        "figure-studio.html",
        "troubleshooting.html",
        "sources.html",
    }
    assert {path.name for path in (site / "zh").glob("*.html")} == expected
    assert {path.name for path in (site / "en").glob("*.html")} == expected
    english = "\n".join(
        path.read_text(encoding="utf-8") for path in (site / "en").glob("*.html")
    )
    assert not any("\u4e00" <= char <= "\u9fff" for char in english)


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
    assert (state.root / "raw" / "behavior_events.csv").is_file()
    assert (state.root / "raw" / "ttl_events.csv").is_file()
    assert (state.root / "raw" / "respiration_reference.npy").is_file()
    assert (state.root / "raw" / "behavioral_states.csv").is_file()


def test_demo_library_covers_probe_geometries_and_behavior(tmp_path: Path):
    catalog = demo_profile_catalog()
    assert {item["key"] for item in catalog} == {
        "neuropixels_decision",
        "tetrode_navigation",
        "microwire_stimulus",
    }
    for item in catalog:
        state = generate_demo_recording(
            tmp_path / item["folder"],
            duration_seconds=1.0,
            profile_key=item["key"],
        )
        positions = np.asarray(state.metadata["contact_positions_um"])
        assert positions.shape == (state.channel_count, 2)
        assert state.metadata["behavior_paradigm"]
        assert state.metadata["recommended_sorters"]
        assert {"choice", "outcome", "reaction_time"} <= set(state.events[0])
        assert state.metadata["behavior_source"]
        assert state.metadata["ttl_source"]


def test_behavior_to_ephys_clock_alignment_is_auditable(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "sync",
        duration_seconds=4,
        channel_count=4,
        sampling_rate=10_000,
    )
    result = synchronize_existing_events(state)
    assert result["matched_count"] == 20
    assert abs(result["drift_ppm"]) > 10
    assert result["max_abs_residual_ms"] < 1.0
    assert state.trials
    assert "alignment_residual_ms" in state.trials[0]


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


def test_non_kilosort_result_never_uses_kilosort_pipeline_title(tmp_path: Path):
    root = tmp_path / "mountainsort5"
    root.mkdir()
    state = ProjectState(
        root=tmp_path,
        sampling_rate=30_000,
        duration_seconds=2.0,
    )
    register_sorting_result(
        state,
        "mountainsort5",
        {1: np.array([0.1, 0.4, 1.2])},
        {
            "sorter": "MountainSort5",
            "backend": "SpikeInterface",
            "version": "test",
            "settings": {"scheme": "2"},
            "result_directory": str(root),
        },
    )
    figure = sorting_diagnostics_figure(state, "pipeline")
    text = " ".join(
        axis.get_title(loc=location)
        for axis in figure.axes
        for location in ("left", "center", "right")
    )
    assert "MountainSort5" in text
    assert "Kilosort" not in text


def test_svg_pdf_png_export_backends_are_available(tmp_path: Path):
    assert run_packaged_figure_export_self_test(tmp_path) == 0
    report = json.loads(
        (tmp_path / "packaged_figure_export_self_test.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["ok"] is True
    assert len(report["outputs"]) == 3


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


def test_elephant_toolkit_produces_real_results(tmp_path: Path):
    state = generate_demo_recording(
        tmp_path / "toolkit",
        duration_seconds=12.0,
        channel_count=8,
    )
    state.sorted_spikes = state.ground_truth

    spike_result = run_spike_train_suite(state)
    lfp_result = run_lfp_suite(state)
    coupling_result = run_spike_field_suite(state, surrogate_count=20)
    respiration_result = run_respiration_case(state)

    assert provider_status()["available"] is True
    assert len(METHOD_CATALOG) >= 5
    assert len(spike_result["rows"]) == len(state.ground_truth)
    assert spike_result["correlation"].shape == (
        len(state.ground_truth),
        len(state.ground_truth),
    )
    assert len(lfp_result["channel_ids"]) == 2
    assert np.asarray(lfp_result["psd"]).shape[0] == 2
    assert len(coupling_result["rows"]) == len(state.ground_truth)
    assert coupling_result["surrogate_count"] == 20
    assert len(respiration_result["rows"]) == 3
    assert "not the original paper dataset" in respiration_result["limitations"][0]

    exported = export_reproducible_bundle(state, tmp_path / "export")
    provenance = json.loads((exported / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["software_versions"]["elephant"] != "not installed"
    assert provenance["spike_train_analysis"]["rows"]
    assert provenance["lfp_analysis"]["band_power"]
    assert provenance["spike_field_analysis"]["rows"]
    assert provenance["case_studies"]["respiration"]["rows"]
    assert (exported / "tables" / "spike_train_statistics.csv").is_file()
    assert (exported / "tables" / "lfp_band_power.csv").is_file()
    assert (exported / "figures" / "spike_field_coupling.svg").is_file()


def test_normalized_multi_sorter_comparison_and_roundtrip(tmp_path: Path):
    state = ProjectState(root=tmp_path / "comparison", sampling_rate=30_000)
    state.ground_truth = {
        0: np.array([0.1, 0.2, 0.3]),
        1: np.array([0.15, 0.25, 0.35]),
    }
    register_sorting_result(
        state,
        "sorter_a",
        {
            10: np.array([0.1001, 0.2001, 0.3001]),
            11: np.array([0.1501, 0.2501, 0.3501]),
            12: np.array([0.72, 0.82]),
        },
        {"sorter": "Sorter A", "backend": "test"},
    )
    register_sorting_result(
        state,
        "sorter_b",
        {
            20: np.array([0.1002, 0.2002, 0.3002]),
            21: np.array([0.1502, 0.2502, 0.3502]),
        },
        {"sorter": "Sorter B", "backend": "test"},
    )
    comparison = compare_sorting_results(state)
    assert comparison["schema"] == "neuroflow.sorting-comparison.v1"
    assert comparison["pairwise"][0]["matched_unit_count"] == 2
    assert comparison["pairwise"][0]["unique_units_a"] == 1
    assert comparison["consensus"]["unit_count"] == 2
    assert comparison["ground_truth"]["sorter_b"]["mean_f1"] == 1.0
    assert sorting_diagnostics_figure(state, "comparison").axes

    activate_sorting_result(state, "sorter_a")
    restored = load_project(save_project(state))
    assert set(restored.sorting_results) == {"sorter_a", "sorter_b"}
    assert restored.active_sorter_key == "sorter_a"
    assert set(restored.sorted_spikes) == {10, 11, 12}
    assert set(restored.ground_truth) == {0, 1}
    assert restored.sorting_provenance["sorter_b"]["time_unit"] == "seconds"
