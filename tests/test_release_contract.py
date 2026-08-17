import json
import tomllib
from pathlib import Path

import neuroephys as ne

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
    assert PRODUCT_VERSION == "1.0.0"
    assert ne.__version__ == PRODUCT_VERSION
    assert metadata["project"]["name"] == "neuroephys-ai"
    assert metadata["project"]["version"] == PRODUCT_VERSION


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
