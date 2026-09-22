"""Data-driven, vector-preserving multi-panel publication layouts.

Grouping follows scientific role, never the sign or significance of a result.
Every exported source figure is assigned to a main or extended-data figure.
"""
from __future__ import annotations

import copy
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from matplotlib.transforms import Bbox
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath
from matplotlib.text import Text
from matplotlib import rc_context

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
_RENDER_APP = None

THEMES = (
    ("main", "Recording quality and behavioral context", (
        "raw_qc", "unit_qc", "behavior")),
    ("main", "Event-aligned unit and population responses", (
        "raster_psth_population", "population_ordered_heatmap")),
    ("main", "Population dynamics across trials and conditions", (
        "population_single_trial", "population_conditions", "population_pca")),
    ("main", "Effect sizes, uncertainty and prediction", (
        "statistics", "decoding", "regression")),
    ("supplementary", "Complete behavioral repertoire", (
        "behavior_spectrum_animals", "behavior_spectrum_by_behavior")),
    ("supplementary", "Spike-train and timing diagnostics", (
        "spike_train_statistics", "spike_train_relationships")),
    ("supplementary", "Decoder model and feature diagnostics", (
        "decoding",)),
    ("supplementary", "Functional relationship diagnostics", (
        "connectivity_ccg_examples", "connectivity_network", "connectivity_distance")),
    ("supplementary", "Field potentials and spike-field coupling", (
        "lfp_psd", "lfp_coherence", "lfp_spectrogram", "spike_field_coupling")),
    ("supplementary", "Separate method-validation case", (
        "respiration_state_analysis", "respiration_phase_amplitude_coupling")),
)


def save_atomic_panels(figure, name: str, output: Path) -> list[dict]:
    """Save each actual data axis as cropped SVG/PNG without shrinking its labels."""
    folder = output / "panels" / name
    folder.mkdir(parents=True, exist_ok=True)
    if not hasattr(figure.canvas, "get_renderer"):
        FigureCanvasAgg(figure)
    figure.canvas.draw()
    # The standard chart constructors use constrained_layout. Hiding sibling
    # axes during crop would otherwise trigger a fresh layout and move this
    # axis after its crop rectangle was measured, truncating labels/titles.
    figure.set_layout_engine(None)
    renderer = figure.canvas.get_renderer()
    data_axes = [axis for axis in figure.axes
                 if axis.axison and axis.get_label() != "<colorbar>"]
    colorbars = [axis for axis in figure.axes if axis.get_label() == "<colorbar>"]
    rows = []
    for index, axis in enumerate(data_axes, 1):
        bounds = axis.get_tightbbox(renderer)
        if bounds is None or bounds.width <= 0 or bounds.height <= 0:
            continue
        # Some Matplotlib versions omit left-aligned long titles and legend
        # text from Axes.get_tightbbox. Preserve their full extents explicitly.
        for artist in axis.findobj(match=Text):
            if not artist.get_visible() or not artist.get_text().strip():
                continue
            extent = artist.get_window_extent(renderer)
            if extent is not None and extent.width > 0 and extent.height > 0:
                bounds = Bbox.union([bounds, extent])
        owned_colorbars = []
        for colorbar in colorbars:
            parent = getattr(getattr(colorbar, "_colorbar", None), "mappable", None)
            if parent is not None and getattr(parent, "axes", None) is axis:
                owned_colorbars.append(colorbar)
                colorbar_bounds = colorbar.get_tightbbox(renderer)
                if colorbar_bounds is not None:
                    bounds = Bbox.union([bounds, colorbar_bounds])
        inches = bounds.transformed(figure.dpi_scale_trans.inverted())
        visible = {other: other.get_visible() for other in figure.axes}
        try:
            for other in figure.axes:
                other.set_visible(other is axis or other in owned_colorbars)
            stem = f"panel_{index:02d}"
            svg = folder / f"{stem}.svg"
            png = folder / f"{stem}.png"
            # Convert font glyphs to vector outlines. QtSvg on Windows can
            # otherwise replace even ASCII axis labels with empty squares.
            with rc_context({"svg.fonttype": "path"}):
                figure.savefig(svg, bbox_inches=inches, pad_inches=0.045,
                               facecolor="white")
            figure.savefig(png, dpi=240, bbox_inches=inches,
                           pad_inches=0.045, facecolor="white")
        finally:
            for other, was_visible in visible.items():
                other.set_visible(was_visible)
        root = ET.parse(svg).getroot()
        view_box = [float(value) for value in root.attrib["viewBox"].split()]
        rows.append({"source_figure": name, "source_axis": index,
                     "title": axis.get_title(loc="left") or axis.get_title() or
                              name.replace("_", " ").title(),
                     "x_label": axis.get_xlabel(), "y_label": axis.get_ylabel(),
                     "source_panel_svg": f"panels/{name}/{stem}.svg",
                     "source_panel_png": f"panels/{name}/{stem}.png",
                     "width_pt": view_box[2], "height_pt": view_box[3],
                     "plotted_data": f"figure_data/{name}.json"})
    (folder / "index.json").write_text(json.dumps(rows, ensure_ascii=False,
                                           indent=2), encoding="utf-8")
    return rows


def _safe_svg_tree(path: Path, prefix: str) -> ET.Element:
    root = ET.parse(path).getroot()
    id_map = {item.attrib["id"]: f"{prefix}_{item.attrib['id']}"
              for item in root.iter() if "id" in item.attrib}
    for item in root.iter():
        if "id" in item.attrib:
            item.set("id", id_map[item.attrib["id"]])
        for key, value in list(item.attrib.items()):
            value = re.sub(r"url\(#([^)]+)\)",
                           lambda hit: f"url(#{id_map.get(hit.group(1), hit.group(1))})",
                           value)
            if value.startswith("#"):
                value = "#" + id_map.get(value[1:], value[1:])
            item.set(key, value)
    return root


def _pages_for_theme(panels: list[dict]) -> list[list[dict]]:
    """Keep one scientific story together; split only when print space requires."""
    pages = []
    offset = 0
    while offset < len(panels):
        remaining = len(panels) - offset
        count = next((n for n in range(min(9, remaining), 0, -1)
                      if _layout_height(panels[offset:offset + n]) <= 480), 1)
        pages.append(panels[offset:offset + count])
        offset += count
    return pages


def _columns_for(panels: list[dict]) -> int:
    if len(panels) <= 2:
        return 2
    if len(panels) == 4 and _height_for_columns(panels, 2) <= 480:
        return 2
    return 3


def _height_for_columns(panels: list[dict], columns: int) -> float:
    width = (500.0 - 12.0 - 18.0 * (columns - 1)) / columns
    total = 12.0
    for index in range(0, len(panels), columns):
        row = panels[index:index + columns]
        total += 20 + max(width * float(panel["height_pt"]) /
                          max(float(panel["width_pt"]), 1)
                          for panel in row) + 16
    return total


def _layout_height(panels: list[dict]) -> float:
    return _height_for_columns(panels, _columns_for(panels))


def _compose_svg(panels: list[dict], exports: Path, destination: Path) -> dict:
    # 500 pt = 176.4 mm, a conservative double-column starting size. The
    # height cap is 480 pt = 169.3 mm. Journal-specific final checks remain.
    width = 500.0
    columns = _columns_for(panels)
    gutter = 18.0
    slot = (width - 12.0 - gutter * (columns - 1)) / columns
    height = _layout_height(panels)
    root = ET.Element(f"{{{SVG}}}svg", {
        "width": f"{width:.2f}pt", "height": f"{height:.2f}pt",
        "viewBox": f"0 0 {width:.2f} {height:.2f}", "version": "1.1"})
    ET.SubElement(root, f"{{{SVG}}}rect", {
        "x": "0", "y": "0", "width": str(width), "height": str(height),
        "fill": "#ffffff"})
    y = 12.0
    positions = []
    for index in range(0, len(panels), columns):
        row = panels[index:index + columns]
        row_height = max(slot * float(item["height_pt"]) /
                         max(float(item["width_pt"]), 1)
                         for item in row)
        for column, panel in enumerate(row):
            x = 6.0 + column * (slot + gutter)
            letter = chr(ord("a") + index + column)
            # SVG text is rendered inconsistently by QtSvg on Windows. Paths
            # remain vector in SVG/PDF and make labels reproducible on export.
            glyph = TextPath((x, -(y + 11)), letter, size=12,
                             prop=FontProperties(weight="bold"))
            segments = []
            for vertices, code in glyph.iter_segments():
                if code == MplPath.MOVETO:
                    segments.append(f"M {vertices[0]:.3f} {-vertices[1]:.3f}")
                elif code == MplPath.LINETO:
                    segments.append(f"L {vertices[0]:.3f} {-vertices[1]:.3f}")
                elif code == MplPath.CURVE3:
                    segments.append(f"Q {vertices[0]:.3f} {-vertices[1]:.3f} {vertices[2]:.3f} {-vertices[3]:.3f}")
                elif code == MplPath.CURVE4:
                    segments.append(f"C {vertices[0]:.3f} {-vertices[1]:.3f} {vertices[2]:.3f} {-vertices[3]:.3f} {vertices[4]:.3f} {-vertices[5]:.3f}")
                elif code == MplPath.CLOSEPOLY:
                    segments.append("Z")
            ET.SubElement(root, f"{{{SVG}}}path", {"d": " ".join(segments),
                                                    "fill": "#1b1a20"})
            source = _safe_svg_tree(exports / panel["source_panel_svg"],
                                    f"p{index + column}")
            draw_width = slot - 10.0
            scale = draw_width / float(panel["width_pt"])
            nested = ET.SubElement(root, f"{{{SVG}}}g", {
                "transform": f"translate({x + 5:.4f} {y + 20:.4f}) scale({scale:.8f})"})
            for child in list(source):
                nested.append(copy.deepcopy(child))
            positions.append({"panel": letter, "x_pt": x + 5, "y_pt": y + 20,
                              "width_pt": draw_width,
                              "height_pt": draw_width * panel["height_pt"] / panel["width_pt"]})
        y += 20 + row_height + 16
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
    return {"width_pt": width, "height_pt": height, "positions": positions}


def _render_composite(svg: Path, png: Path, pdf: Path) -> None:
    """Qt renders SVG paths to a vector PDF; PNG is a preview only."""
    from PySide6.QtCore import QRectF, QSizeF, QMarginsF, Qt
    from PySide6.QtGui import QPainter, QPageSize, QPdfWriter, QImage
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication

    global _RENDER_APP
    _RENDER_APP = QApplication.instance() or QApplication([])
    renderer = QSvgRenderer(str(svg))
    if not renderer.isValid():
        raise ValueError(f"Invalid composite SVG: {svg}")
    box = renderer.viewBoxF()
    image = QImage(max(1, math.ceil(box.width() * 2)),
                   max(1, math.ceil(box.height() * 2)), QImage.Format_RGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, image.width(), image.height()))
    painter.end()
    image.save(str(png), "PNG")
    writer = QPdfWriter(str(pdf))
    writer.setPageSize(QPageSize(QSizeF(box.width() / 72, box.height() / 72),
                                  QPageSize.Inch))
    writer.setResolution(72)
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))
    painter = QPainter(writer)
    renderer.render(painter, QRectF(0, 0, box.width(), box.height()))
    painter.end()


def compose_publication_figures(exports: Path, available: list[str]) -> list[dict]:
    """Return complete main/supplementary figure manifest for any subset."""
    ordered = list(dict.fromkeys(available))
    assigned = set()
    themes = list(THEMES)
    unknown = tuple(name for name in ordered if not any(name in row[2] for row in THEMES))
    if unknown:
        themes.append(("supplementary", "Other complete analysis evidence", unknown))
    result = []
    number = {"main": 0, "supplementary": 0}
    destination = exports / "publication" / "figures"
    destination.mkdir(parents=True, exist_ok=True)
    override_path = exports / "publication" / "author_edits.json"
    overrides = (json.loads(override_path.read_text(encoding="utf-8"))
                 if override_path.is_file() else {})
    for role, story, names in themes:
        panels = []
        for name in names:
            if name not in ordered:
                continue
            assigned.add(name)
            path = exports / "panels" / name / "index.json"
            if path.is_file():
                source_panels = json.loads(path.read_text(encoding="utf-8"))
                if name == "decoding":
                    source_panels = (source_panels[:4] if role == "main" else
                                     source_panels[4:])
                panels.extend(source_panels)
            else:
                if name == "decoding" and role == "supplementary":
                    continue  # A legacy unsplit SVG is already included in main.
                # Older project exports still have a full vector source figure.
                # A new export provides genuine per-axis crops; this fallback
                # keeps their evidence in the layout rather than omitting it.
                source = exports / "figures" / f"{name}.svg"
                if not source.is_file():
                    raise FileNotFoundError(f"Figure SVG missing for {name}: {source}")
                box = [float(value) for value in ET.parse(source).getroot().attrib["viewBox"].split()]
                panels.append({"source_figure": name, "source_axis": 0,
                               "title": name.replace("_", " ").title(),
                               "source_panel_svg": f"figures/{name}.svg",
                               "source_panel_png": f"figures/{name}.png",
                               "width_pt": box[2], "height_pt": box[3],
                               "plotted_data": f"figure_data/{name}.json"})
        for page in _pages_for_theme(panels):
            number[role] += 1
            label = (f"Figure {number[role]}" if role == "main" else
                     f"Extended Data Figure {number[role]}")
            edited = overrides.get(label, {})
            rank = {path: index for index, path in enumerate(edited.get("panel_order", []))}
            page.sort(key=lambda panel: rank.get(panel["source_panel_svg"],
                                                  len(rank) + panels.index(panel)))
            stem = (f"figure_{number[role]:02d}" if role == "main" else
                    f"extended_data_figure_{number[role]:02d}")
            svg = destination / f"{stem}.svg"
            geometry = _compose_svg(page, exports, svg)
            _render_composite(svg, destination / f"{stem}.png",
                              destination / f"{stem}.pdf")
            result.append({"figure": label, "role": role, "story_role": story,
                           "composite_svg": f"publication/figures/{stem}.svg",
                           "composite_png": f"publication/figures/{stem}.png",
                           "composite_pdf": f"publication/figures/{stem}.pdf",
                           "layout": geometry,
                           "panels": [{"panel": chr(ord("a") + index),
                                       "figure_name": panel["source_figure"],
                                       "source_axis": panel["source_axis"],
                                       "array_axis_index": max(0, panel["source_axis"] - 1),
                                       "title": panel["title"],
                                       "source_panel_svg": panel["source_panel_svg"],
                                       "source_panel_png": panel["source_panel_png"],
                                       "plotted_data": panel["plotted_data"],
                                       "width_pt": panel["width_pt"],
                                       "height_pt": panel["height_pt"]}
                                      for index, panel in enumerate(page)],
                           "author_interpretation": ""})
    if assigned != set(ordered):
        raise AssertionError(f"Unassigned exported figures: {set(ordered) - assigned}")
    expected = {Path(item[key]).name for item in result
                for key in ("composite_svg", "composite_png", "composite_pdf")}
    for stale in destination.iterdir():
        if (stale.is_file() and stale.name not in expected and
                re.fullmatch(r"(?:figure|extended_data_figure)_\d{2}\.(?:svg|png|pdf)",
                             stale.name)):
            stale.unlink()
    return result


def rebuild_publication_figure(exports: Path, figure: dict) -> None:
    """Re-render one author-reordered figure from its original vector panels."""
    path = exports / figure["composite_svg"]
    geometry = _compose_svg(figure["panels"], exports, path)
    _render_composite(path, exports / figure["composite_png"],
                      exports / figure["composite_pdf"])
    figure["layout"] = geometry
