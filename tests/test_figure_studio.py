import os

import matplotlib.pyplot as plt
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFormLayout

from neuroflow.figure_studio import FigureStudioDialog, figure_artist_catalog

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_figure_studio_catalogs_editable_objects():
    figure, axis = plt.subplots()
    axis.plot([0, 1], [1, 2], label="mean")
    axis.scatter([0.2, 0.8], [1.1, 1.7], label="trials")
    axis.bar([0.4], [0.5], label="count")
    axis.imshow([[0, 1], [2, 3]], extent=(0, 1, 0, 1), alpha=0.2)
    axis.text(0.5, 0.5, "annotation")
    axis.legend()
    catalog = figure_artist_catalog(figure)
    kinds = [item["kind"] for item in catalog]
    names = [item["name"] for item in catalog]
    assert kinds.count("figure") == 1
    assert kinds.count("axis") == 1
    assert "mean" in names
    assert "trials" in names
    assert any(name.startswith("Patch / bar") for name in names)
    assert any(name.startswith("Image / heatmap") for name in names)
    assert "annotation" in names
    plt.close(figure)


def test_figure_studio_restores_scatter_style():
    app = QApplication.instance() or QApplication([])
    figure, axis = plt.subplots()
    scatter = axis.scatter([0.2, 0.8], [1.1, 1.7], c="#176c57", s=[20, 40])
    dialog = FigureStudioDialog(figure, "en_US")
    target_item = None
    for top_index in range(dialog.tree.topLevelItemCount()):
        top = dialog.tree.topLevelItem(top_index)
        for child_index in range(top.childCount()):
            child = top.child(child_index)
            if child.data(0, Qt.UserRole) is scatter:
                target_item = child
                break
    assert target_item is not None
    original_facecolors = np.asarray(scatter.get_facecolors()).copy()
    original_sizes = np.asarray(scatter.get_sizes()).copy()
    scatter.set_facecolor("#ff0000")
    scatter.set_sizes([100, 120])
    dialog.tree.setCurrentItem(target_item)
    dialog._reset_selected()
    assert np.allclose(scatter.get_facecolors(), original_facecolors)
    assert np.allclose(scatter.get_sizes(), original_sizes)
    dialog.close()
    app.processEvents()
    plt.close(figure)


def test_figure_studio_exposes_prism_style_axis_controls():
    app = QApplication.instance() or QApplication([])
    figure, axis = plt.subplots(figsize=(7, 5))
    axis.plot([0, 1], [1, 2], label="mean")
    dialog = FigureStudioDialog(figure, "en_US")
    axis_item = None
    for index in range(dialog.tree.topLevelItemCount()):
        item = dialog.tree.topLevelItem(index)
        if item.data(0, Qt.UserRole) is axis:
            axis_item = item
            break
    assert axis_item is not None
    dialog.tree.setCurrentItem(axis_item)
    labels = {
        dialog.editor_layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
        .widget()
        .text()
        for row in range(dialog.editor_layout.rowCount())
        if dialog.editor_layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
        and dialog.editor_layout.itemAt(row, QFormLayout.ItemRole.LabelRole).widget()
    }
    assert "X-axis length (inches)" in labels
    assert "Bottom X axis" in labels
    assert "X major interval" in labels
    assert "X minor divisions" in labels
    assert "X major grid" in labels
    assert "Y minor grid" in labels
    assert "Vertical lines at X" in labels
    assert "Legend edge width" in labels
    dialog.close()
    app.processEvents()
    plt.close(figure)
