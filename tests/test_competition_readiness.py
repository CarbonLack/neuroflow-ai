from pathlib import Path

import numpy as np

from neuroflow.competition_readiness import readiness_snapshot, write_readiness_bundle
from neuroflow.models import ProjectState


def test_readiness_never_claims_missing_evidence(tmp_path: Path):
    state = ProjectState(root=tmp_path / "project", name="Demo")
    state.root.mkdir()
    state.sorted_spikes = {1: np.array([0.1, 0.2])}
    state.qc = {"bad_channels": []}

    snapshot = readiness_snapshot(
        state,
        workspace=tmp_path,
        ai_configured=False,
        installed_sorters=["kilosort4", "mountainsort5"],
    )

    checks = {item["id"]: item for item in snapshot["checks"]}
    assert checks["project"]["ready"] is True
    assert checks["three_sorters"]["ready"] is False
    assert checks["figures"]["ready"] is False
    assert checks["ai"]["ready"] is False
    output = write_readiness_bundle(snapshot, tmp_path / "bundle")
    assert output.exists()
    assert "[ ] Exported figures exist" in output.read_text(encoding="utf-8")


def test_readiness_recognizes_built_offline_manual(tmp_path: Path):
    manual = tmp_path / "docs" / "site" / "zh" / "index.html"
    manual.parent.mkdir(parents=True)
    manual.write_text("manual", encoding="utf-8")

    snapshot = readiness_snapshot(
        None,
        workspace=tmp_path,
        ai_configured=False,
    )

    checks = {item["id"]: item for item in snapshot["checks"]}
    assert checks["offline_docs"]["ready"] is True
