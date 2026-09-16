import numpy as np
from matplotlib.figure import Figure
from matplotlib.colors import to_hex
from PySide6.QtWidgets import QApplication, QWidget

from neuroflow.figure_studio import FigureStudioDialog, figure_artist_catalog
from neuroflow.figures import unit_metrics_figure
from neuroflow.models import ProjectState
from neuroflow.project import save_project, load_project
from neuroflow.publication_style import DEFAULT_STYLE, apply_publication_style, publication_figure


@publication_figure
def example_figure(state, view="test"):
    fig = Figure()
    a, b = fig.subplots(2)
    for axis, title in ((a, "Raw traces"), (b, "Unit count")):
        axis.plot([1, 2, 3], [2, 4, 1], color="#9f3fb4", label="condition")
        axis.set_title(title, loc="left")
        axis.set_xlabel("Time (s)")
        axis.legend()
    return fig


def test_style_preserves_science_and_colormap(tmp_path):
    fig = example_figure(ProjectState(tmp_path))
    axis = fig.axes[0]
    axis.set_xscale("log")
    axis.set_xlim(3, 1)
    axis.set_ylim(-2, 5)
    mesh = axis.imshow([[0, 1], [2, 3]], cmap="coolwarm", vmin=-4, vmax=4)
    before = (axis.get_xlim(), axis.get_ylim(), axis.get_position().bounds)
    points = axis.lines[0].get_xydata().copy()
    apply_publication_style(fig, {"font_size": 7, "axis_width": 0.5})
    assert before == (axis.get_xlim(), axis.get_ylim(), axis.get_position().bounds)
    assert axis.get_xscale() == "log"
    np.testing.assert_equal(points, axis.lines[0].get_xydata())
    assert mesh.get_clim() == (-4, 4) and mesh.get_cmap().name == "coolwarm"
    assert axis.get_title(loc="left") == "Raw traces"
    assert not axis.spines["top"].get_visible()
    assert not any(line.get_visible() for line in axis.get_ygridlines())
    assert axis.xaxis.label.get_fontsize() == 7
    assert to_hex(axis.lines[0].get_color()) == "#b7a0c7"


def test_panel_names_and_initial_selection(tmp_path):
    app = QApplication.instance() or QApplication([])
    fig = example_figure(ProjectState(tmp_path))
    assert figure_artist_catalog(fig)[1]["name"] == "Raw traces"
    dialog = FigureStudioDialog(fig, initial_axis=fig.axes[1])
    assert "Unit count" in dialog.tree.currentItem().text(0)
    assert "子图 2" in dialog.target_heading.text()
    assert dialog.field_widgets["Graph title"].text() == "Unit count"
    assert dialog.style_scope.checkedId() == 0
    dialog.close()
    app.processEvents()


def test_shared_style_scope_and_project_roundtrip(tmp_path):
    app = QApplication.instance() or QApplication([])
    state = ProjectState(tmp_path, name="style-test")
    parent = QWidget()
    parent.state = state
    parent._mark_project_dirty = lambda: None
    fig = example_figure(state)
    dialog = FigureStudioDialog(fig, parent=parent, initial_axis=fig.axes[1])
    dialog.style_controls["font_size"].setValue(11)
    dialog._apply_shared_style()
    assert fig.axes[0].xaxis.label.get_fontsize() == DEFAULT_STYLE["font_size"]
    assert fig.axes[1].xaxis.label.get_fontsize() == 11
    save_project(state)
    reopened = load_project(tmp_path)
    refreshed = example_figure(reopened)
    assert refreshed.axes[1].xaxis.label.get_fontsize() == 11
    assert refreshed.axes[0].xaxis.label.get_fontsize() == 8
    dialog.style_scope.button(2).setChecked(True)
    dialog.style_controls["font_size"].setValue(9)
    dialog._apply_shared_style()
    assert "figure_styles" not in state.metadata
    assert all(ax.xaxis.label.get_fontsize() == 9 for ax in example_figure(state, "other").axes)
    dialog.close()
    parent.close()
    app.processEvents()


def test_default_export_has_editable_text(tmp_path):
    fig = example_figure(ProjectState(tmp_path))
    path = tmp_path / "figure.svg"
    fig.savefig(path)
    assert "<text" in path.read_text(encoding="utf-8")


def test_palette_switching_is_reversible_and_matches_legend(tmp_path):
    fig = example_figure(ProjectState(tmp_path))
    axis = fig.axes[0]
    for palette, colour in (("muted", "#b7a0c7"), ("accessible", "#0072b2"), ("original", "#9f3fb4"), ("muted", "#b7a0c7")):
        apply_publication_style(fig, {"palette": palette})
        assert to_hex(axis.lines[0].get_color()) == colour
        assert to_hex(axis.get_legend().legend_handles[0].get_color()) == colour


def test_unit_metrics_overview_explains_colours_and_uses_real_unit_ids(tmp_path):
    state = ProjectState(tmp_path)
    state.metadata["language"] = "en_US"
    state.unit_metrics = [
        {
            "unit_id": 7,
            "firing_rate_hz": 4.2,
            "snr": 6.1,
            "isi_violation_rate": 0.004,
            "label": "candidate_single_unit",
        },
        {
            "unit_id": 42,
            "firing_rate_hz": 8.8,
            "snr": 2.5,
            "isi_violation_rate": 0.08,
            "label": "review_required",
        },
    ]
    figure = unit_metrics_figure(state)
    legend = figure.axes[0].get_legend()
    assert legend is not None
    assert [item.get_text() for item in legend.get_texts()] == [
        "Automatic label: candidate single unit",
        "Automatic label: review required",
    ]
    assert [int(value) for value in figure.axes[1].get_xticks()] == [7, 42]


def test_title_and_background_edits_preserve_ranges_and_locators(tmp_path):
    app = QApplication.instance() or QApplication([])
    fig = example_figure(ProjectState(tmp_path))
    axis = fig.axes[0]
    axis.set_xscale("log")
    axis.set_xlim(2.987654321, 1.012345678)
    axis.set_ylim(-1.12345678, 5.87654321)
    axis.grid(True, axis="y")
    before = (axis.get_xlim(), axis.get_ylim(), axis.get_position().bounds)
    locators = (axis.xaxis.get_major_locator(), axis.xaxis.get_minor_locator())
    dialog = FigureStudioDialog(fig, initial_axis=axis)
    dialog.field_widgets["Graph title"].setText("Updated title")
    for binding in dialog.bindings:
        binding.apply()
    assert axis.get_title(loc="left") == "Updated title"
    assert before == (axis.get_xlim(), axis.get_ylim(), axis.get_position().bounds)
    assert locators == (axis.xaxis.get_major_locator(), axis.xaxis.get_minor_locator())
    assert any(line.get_visible() for line in axis.get_ygridlines())
    dialog.field_widgets["Plot-area background"].set_color("#eeeeee")
    for binding in dialog.bindings:
        binding.apply()
    assert before == (axis.get_xlim(), axis.get_ylim(), axis.get_position().bounds)
    dialog.close()
    app.processEvents()
