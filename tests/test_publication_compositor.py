import json

from matplotlib.figure import Figure
from PySide6.QtWidgets import QApplication

from neuroflow.publication_compositor import (
    compose_publication_figures, save_atomic_panels,
)
from neuroflow.publication_ui import PublicationGallery


def test_composite_is_real_vector_artwork_and_edit_persists(tmp_path):
    app = QApplication.instance() or QApplication([])
    figure = Figure(figsize=(6, 3))
    first, second = figure.subplots(1, 2)
    first.plot([0, 1], [1, 2])
    first.set_title("Signal")
    second.bar([0, 1], [2, 1])
    second.set_title("Response")
    save_atomic_panels(figure, "behavior", tmp_path)
    groups = compose_publication_figures(tmp_path, ["behavior"])
    assert len(groups) == 1
    assert len(groups[0]["panels"]) == 2
    assert groups[0]["layout"]["width_pt"] <= 500
    assert groups[0]["layout"]["height_pt"] <= 480
    svg = (tmp_path / groups[0]["composite_svg"]).read_text(encoding="utf-8")
    assert "<path" in svg and "<image" not in svg  # vector, not a PNG wrapper
    assert (tmp_path / groups[0]["composite_pdf"]).stat().st_size > 1000

    (tmp_path / "publication" / "storyboard.json").write_text(
        json.dumps({"figures": groups}), encoding="utf-8")
    gallery = PublicationGallery()
    assert gallery.load(tmp_path)
    assert gallery.current_figure_name == "Figure 1"
    gallery.tree.setCurrentItem(gallery.tree.topLevelItem(0).child(0))
    gallery._move_selected(1)
    saved = json.loads((tmp_path / "publication" / "storyboard.json").read_text("utf-8"))
    assert saved["figures"][0]["panels"][0]["source_axis"] == 2
    edits = json.loads((tmp_path / "publication" / "author_edits.json").read_text("utf-8"))
    assert edits["Figure 1"]["panel_order"][0].endswith("panel_02.svg")
    assert compose_publication_figures(tmp_path, ["behavior"])[0]["panels"][0]["source_axis"] == 2
    gallery.close()
    assert app is not None
