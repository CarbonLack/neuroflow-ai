import json

import matplotlib.pyplot as plt
import numpy as np
from PySide6.QtWidgets import QApplication

from neuroflow.ai_project_bridge import ProjectQueries
from neuroflow.figure_data import save_figure_data
from neuroflow.models import ProjectState
from neuroflow.publication_ui import PublicationGallery


def test_plotted_values_and_ai_query_round_trip(tmp_path):
    state = ProjectState(root=tmp_path)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [5, 8, 3], label="rate")
    ax.scatter([0.5, 1.5], [6, 7])
    output = tmp_path / "exports"
    manifest = save_figure_data(fig, "behavior", output, state)
    plt.close(fig)
    assert manifest["source_sections"] == ["events", "trials"]
    arrays = np.load(output / "figure_data" / "behavior.npz")
    assert arrays["axis0_line0_y"].tolist() == [5, 8, 3]
    queries = ProjectQueries(state, "export", "assistant")
    catalog = queries.figure_data()["result"]
    assert "behavior" in catalog["figures"]
    actual = queries.figure_data("behavior", "axis0_line0_y")["result"]
    assert actual["values"] == [5, 8, 3]


def test_native_publication_gallery_loads_panel(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    exports = tmp_path / "exports"
    (exports / "publication").mkdir(parents=True)
    (exports / "figures").mkdir()
    (exports / "figure_data").mkdir()
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    from PySide6.QtGui import QImage
    QImage(image.data, 4, 4, 12, QImage.Format_RGB888).copy().save(
        str(exports / "figures" / "behavior.png"))
    (exports / "publication" / "storyboard.json").write_text(json.dumps({
        "figures": [{"figure": "Figure 1", "story_role": "Behavior", "panels": [{
            "panel": "a", "title": "Behavioral context", "caption_draft": "Event timing.",
            "source_svg": "figures/behavior.svg"}]}]}), encoding="utf-8")
    (exports / "figure_data" / "behavior.json").write_text(json.dumps({
        "source_sections": ["events"]}), encoding="utf-8")
    gallery = PublicationGallery()
    assert gallery.load(exports)
    assert gallery.current_figure_name == "behavior"
    assert "Event timing" in gallery.caption.text()
    assert "figure_data/behavior.json" in gallery.caption.text()
    gallery.close()


def test_ai_can_map_composite_panel_to_exact_plotted_data(tmp_path):
    state = ProjectState(root=tmp_path)
    folder = tmp_path / "exports" / "publication"
    folder.mkdir(parents=True)
    (folder / "storyboard.json").write_text(json.dumps({"figures": [{
        "figure": "Figure 1", "story_role": "Recording quality",
        "panels": [{"panel": "a", "figure_name": "raw_qc", "source_axis": 1,
                    "title": "Noise", "caption_draft": "Per-channel noise.",
                    "plotted_data": "figure_data/raw_qc.json"}]}]}), encoding="utf-8")
    queries = ProjectQueries(state, "export", "assistant")
    assert queries.context()["result"]["publication_figures"][0]["figure"] == "Figure 1"
    data = queries.figure_data("Figure 1")["result"]
    assert data["panels"][0]["source_chart"] == "raw_qc"
    assert data["panels"][0]["plotted_data"] == "figure_data/raw_qc.json"
