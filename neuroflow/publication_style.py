"""Presentation-only figure styles. Sources and limits: docs/FIGURE_STYLE_STANDARD_ZH.md."""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import inspect

from matplotlib import colors, rcParams
from matplotlib.collections import PathCollection


DEFAULT_STYLE = {
    "font_family": "Arial", "font_size": 8.0, "title_size": 9.0,
    "line_width": 0.8, "axis_width": 0.75, "tick_length": 3.0,
    "grid": False, "top_right": False, "text_color": "#222222",
    "background": "#ffffff", "palette": "muted", "dpi": 600,
}
PRESETS = {
    "research": DEFAULT_STYLE,
    "nature": {**DEFAULT_STYLE, "font_size": 7.0, "title_size": 7.0},
    "presentation": {**DEFAULT_STYLE, "font_size": 12.0, "title_size": 14.0, "axis_width": 1.0, "line_width": 1.5},
}
# Stable mapping, not a per-artist counter: a category keeps its colour across panels.
ACCESSIBLE_MAP = {
    "#9f3fb4": "#0072b2", "#238a67": "#d55e00",
    "#b47c25": "#e69f00", "#6a5a88": "#009e73",
}
MUTED_MAP = {
    "#9f3fb4": "#b7a0c7", "#238a67": "#a4cba0",
    "#b47c25": "#d4bb91", "#6a5a88": "#9eafc5",
}


def style_values(value=None):
    result = dict(DEFAULT_STYLE)
    result.update({k: v for k, v in (value or {}).items() if k in result})
    for key in ("font_size", "title_size", "line_width", "axis_width", "tick_length", "dpi"):
        result[key] = float(result[key])
        if not 0 < result[key] <= (1200 if key == "dpi" else 100):
            raise ValueError(f"Invalid style value: {key}")
    for key in ("text_color", "background"):
        result[key] = colors.to_hex(result[key])
    if result["palette"] not in {"muted", "accessible", "original"}:
        raise ValueError("Unknown palette")
    return result


def panel_title(axis, index=1):
    return next((axis.get_title(loc=loc).strip() for loc in ("left", "center", "right") if axis.get_title(loc=loc).strip()), "") or axis.get_ylabel() or axis.get_xlabel() or f"Panel {index}"


def _mapped(value, palette):
    try:
        rgba = colors.to_rgba(value)
        original = colors.to_hex(rgba)
        canonical = {v: k for mapping in (ACCESSIBLE_MAP, MUTED_MAP) for k, v in mapping.items()}.get(original, original)
        mapping = {"muted": MUTED_MAP, "accessible": ACCESSIBLE_MAP, "original": {}}[palette]
        return colors.to_rgba(mapping.get(canonical, canonical), rgba[3])
    except (ValueError, TypeError):
        return value


def apply_publication_style(figure, value=None, axes=None):
    """Never change data, limits, locators, normalization, aspect, or axes geometry."""
    style = style_values(value)
    selected = list(figure.axes if axes is None else axes)
    families = [style["font_family"], "Microsoft YaHei", "DejaVu Sans"]
    rcParams["pdf.fonttype"] = 42
    rcParams["ps.fonttype"] = 42
    rcParams["svg.fonttype"] = "none"
    rcParams["savefig.dpi"] = style["dpi"]
    if axes is None:
        figure.set_facecolor(style["background"])
        figure._neuroflow_publication_style = deepcopy(style)
    for axis in selected:
        axis._neuroflow_publication_style = deepcopy(style)
        if not axis.axison:
            continue  # instructional text / empty states are not scientific axes
        axis.set_facecolor(style["background"])
        is_colorbar = axis.get_label() == "<colorbar>"
        for loc in ("left", "center", "right"):
            title = {"left": axis._left_title, "center": axis.title, "right": axis._right_title}[loc]
            title.set_fontfamily(families)
            title.set_fontsize(style["title_size"])
            title.set_color(style["text_color"])
        for label in (axis.xaxis.label, axis.yaxis.label):
            label.set_fontfamily(families)
            label.set_fontsize(style["font_size"])
            label.set_color(style["text_color"])
        axis.tick_params(which="both", colors=style["text_color"], labelsize=style["font_size"], width=style["axis_width"], direction="out")
        axis.tick_params(which="major", length=style["tick_length"])
        for label in axis.get_xticklabels() + axis.get_yticklabels() + [axis.xaxis.get_offset_text(), axis.yaxis.get_offset_text()]:
            label.set_fontfamily(families)
            label.set_fontsize(style["font_size"])
        if not is_colorbar:
            axis.grid(False, which="both", axis="both")
            if style["grid"]:
                axis.grid(True, axis="y", color="#d6d6d6", linewidth=0.4, alpha=0.6)
            for name, spine in axis.spines.items():
                if name in ("top", "right"):
                    spine.set_visible(bool(style["top_right"]))
                spine.set_color(style["text_color"])
                spine.set_linewidth(style["axis_width"])
        for line in axis.lines:
            line.set_linewidth(style["line_width"])
            line.set_color(_mapped(line.get_color(), style["palette"]))
        for patch in axis.patches:
            patch.set_facecolor(_mapped(patch.get_facecolor(), style["palette"]))
        for collection in axis.collections:
            # Do not turn a quantitative heatmap/scatter colour array into categories.
            if collection.get_array() is None and len(collection.get_facecolors()):
                collection.set_facecolors([_mapped(c, style["palette"]) for c in collection.get_facecolors()])
        legend = axis.get_legend()
        if legend:
            legend.set_frame_on(False)
            for text in [*legend.get_texts(), legend.get_title()]:
                text.set_fontfamily(families)
                text.set_fontsize(style["font_size"])
                text.set_color(style["text_color"])
            for handle in legend.legend_handles:
                if hasattr(handle, "get_color"):
                    handle.set_color(_mapped(handle.get_color(), style["palette"]))
                elif hasattr(handle, "get_facecolor"):
                    face = handle.get_facecolor()
                    if isinstance(handle, PathCollection):
                        handle.set_facecolors([_mapped(c, style["palette"]) for c in face])
                    else:
                        handle.set_facecolor(_mapped(face, style["palette"]))
    return figure


def publication_figure(function):
    """Apply project-wide and per-view/panel overrides to GUI and Python figures alike."""
    signature = inspect.signature(function)

    @wraps(function)
    def wrapped(*args, **kwargs):
        arguments = signature.bind(*args, **kwargs)
        arguments.apply_defaults()
        state = arguments.arguments.get("state")
        figure = function(*args, **kwargs)
        key = function.__name__ + ":" + str(arguments.arguments.get("view", "default"))
        figure._neuroflow_style_key = key
        metadata = getattr(state, "metadata", {})
        base = style_values(metadata.get("publication_style"))
        overrides = metadata.get("figure_styles", {}).get(key, {})
        apply_publication_style(figure, {**base, **overrides.get("figure", {})})
        for index, axis in enumerate(figure.axes):
            if str(index) in overrides.get("panels", {}):
                apply_publication_style(figure, {**base, **overrides.get("figure", {}), **overrides["panels"][str(index)]}, [axis])
        return figure
    return wrapped
