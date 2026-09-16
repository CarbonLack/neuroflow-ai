import json
from pathlib import Path

from neuroflow.models import ProjectState
from neuroflow.publication_report import write_publication_report


def _svg(path: Path):
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">'
        '<text style="font-size: 8px">Test</text></svg>',
        encoding="utf-8",
    )


def test_storyboard_assigns_every_figure_and_panel_letter(tmp_path: Path):
    figures = tmp_path / "figures"
    figures.mkdir()
    names = ["behavior", "raw_qc", "raster_psth_population", "statistics", "extra_diagnostic"]
    for name in names:
        _svg(figures / f"{name}.svg")
    state = ProjectState(root=tmp_path / "project", name="Publication test")

    write_publication_report(state, tmp_path, names)
    story = json.loads((tmp_path / "publication" / "storyboard.json").read_text(encoding="utf-8"))
    assigned = [panel["figure_name"] for figure in story["figures"] for panel in figure["panels"]]

    assert sorted(assigned) == sorted(names)
    assert all(panel["panel"] for figure in story["figures"] for panel in figure["panels"])
    assert any(figure["role"] == "supplementary" for figure in story["figures"])
