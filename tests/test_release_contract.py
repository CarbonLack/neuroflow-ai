import json
import tomllib
from pathlib import Path

import neuroephys as ne
import numpy as np

from neuroephys.cli import main
from neuroflow.paths import default_workspace, initialize_workspace
from neuroflow.product import PRODUCT_NAME, PRODUCT_VERSION
from neuroflow.self_test import run_packaged_startup_self_test


def test_release_identity_is_consistent():
    metadata = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )

    assert PRODUCT_NAME == "NeuroEphys AI"
    assert PRODUCT_VERSION == "1.1.1"
    assert ne.__version__ == PRODUCT_VERSION
    assert metadata["project"]["name"] == "neuroephys-ai"
    assert metadata["project"]["version"] == PRODUCT_VERSION


def test_release_workflow_does_not_hardcode_an_old_version():
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "release.yml"
    ).read_text(encoding="utf-8")

    assert "release/v1.0.0/*" not in workflow
    assert workflow.count("release/v*/*") == 2


def test_workspace_override_creates_stable_layout(tmp_path: Path, monkeypatch):
    requested = tmp_path / "managed-workspace"
    monkeypatch.setenv("NEUROEPHYS_HOME", str(requested))

    assert default_workspace() == requested.resolve()
    root = initialize_workspace()
    assert root == requested.resolve()
    assert all(
        (root / name).is_dir()
        for name in ("projects", "DemoData", "cache", "logs")
    )


def test_public_api_creates_versioned_project(tmp_path: Path):
    project = ne.create_simulated_project(
        tmp_path / "python-api-project",
        duration_seconds=1.0,
        sampling_rate=5_000.0,
        channel_count=4,
    )

    assert isinstance(project, ne.ProjectState)
    qc = ne.run_raw_qc(project, seconds=0.5)
    assert len(qc["channel_rms"]) == 4
    manifest = json.loads(
        (project.root / "neuroflow_project.json").read_text(encoding="utf-8")
    )
    assert manifest["application"] == PRODUCT_NAME
    assert manifest["application_version"] == PRODUCT_VERSION


def test_cli_info_is_machine_readable(capsys):
    assert main(["info", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["application"] == PRODUCT_NAME
    assert payload["version"] == PRODUCT_VERSION
    assert payload["python"].startswith("3.12.")


def test_cli_population_and_connectivity_write_project_results(
    tmp_path: Path,
    capsys,
):
    state = ne.ProjectState(
        root=tmp_path / "cli-project",
        name="CLI project",
        source_type="processed",
        duration_seconds=10.0,
        events=[
            {"time_seconds": 1.0, "condition": "go"},
            {"time_seconds": 3.0, "condition": "go"},
            {"time_seconds": 5.0, "condition": "stop"},
        ],
        sorted_spikes={
            1: np.array([0.9, 1.1, 3.1, 5.1]),
            2: np.array([0.95, 1.15, 3.15, 5.15]),
            3: np.array([1.2, 3.2, 5.2]),
        },
    )
    ne.save_project(state)

    assert (
        main(
            [
                "population",
                str(state.root),
                "--event-label",
                "go",
                "--window-start",
                "-0.2",
                "--window-stop",
                "0.3",
                "--bin-ms",
                "10",
                "--json",
            ]
        )
        == 0
    )
    population = json.loads(capsys.readouterr().out)
    assert population["trial_count"] == 2
    assert population["unit_count"] == 3

    assert (
        main(
            [
                "connectivity",
                str(state.root),
                "--min-rate-hz",
                "0",
                "--iterations",
                "5",
                "--max-pairs",
                "2",
                "--multiple-comparison",
                "none",
                "--json",
            ]
        )
        == 0
    )
    connectivity = json.loads(capsys.readouterr().out)
    assert connectivity["candidate_pair_count"] == 3
    assert connectivity["tested_pair_count"] == 2
    restored = ne.load_project(state.root)
    assert "population_dynamics" in restored.spike_train_analysis
    assert "connectivity" in restored.spike_train_analysis


def test_startup_self_test_constructs_real_window(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    assert run_packaged_startup_self_test(tmp_path) == 0
    payload = json.loads(
        (tmp_path / "packaged_startup_self_test.json").read_text(encoding="utf-8")
    )
    assert payload["ok"] is True
    assert payload["window_title"].startswith(PRODUCT_NAME)
    assert payload["window_title"].endswith(f"· v{PRODUCT_VERSION}")
    assert payload["page_count"] >= 2
