"""Export exact plotted artist arrays alongside each publication figure."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


SOURCE_SECTIONS = {
    "raw_qc": ["qc"], "unit_qc": ["unit_metrics", "sorted_spikes"],
    "behavior": ["events", "trials"],
    "raster_psth_population": ["analysis", "events", "sorted_spikes"],
    "statistics": ["statistics", "analysis"],
    "decoding": ["decoding", "analysis"],
    "regression": ["regression", "analysis"],
}


def save_figure_data(figure, name: str, output: Path, state,
                     source_sections: list[str] | None = None) -> dict:
    """Preserve artist values, with a manifest that distinguishes unsupported artists."""
    folder = output / "figure_data"
    folder.mkdir(parents=True, exist_ok=True)
    arrays = {}
    axes = []
    for axis_index, axis in enumerate(figure.axes):
        if axis.get_label() == "<colorbar>" or not axis.axison:
            continue
        panel = {"title": axis.get_title(), "xlabel": axis.get_xlabel(),
                 "ylabel": axis.get_ylabel(), "xlim": list(axis.get_xlim()),
                 "ylim": list(axis.get_ylim()), "artists": [], "unsupported_artists": []}

        def add(kind, values, label=""):
            keys = {}
            for field, value in values.items():
                key = f"axis{axis_index}_{kind}{len(panel['artists'])}_{field}"
                try:
                    numeric = np.asarray(value, dtype=float)
                except (TypeError, ValueError):
                    panel["unsupported_artists"].append(f"{kind}.{field}: non-numeric")
                    continue
                arrays[key] = numeric
                keys[field] = {"array": key, "shape": list(numeric.shape)}
            if keys:
                panel["artists"].append({"kind": kind, "label": label, "values": keys})

        for line in axis.lines:
            add("line", {"x": line.get_xdata(orig=False), "y": line.get_ydata(orig=False)}, line.get_label())
        for image in axis.images:
            add("image", {"pixels": image.get_array(), "extent": image.get_extent()}, image.get_label())
        for collection in axis.collections:
            kind = type(collection).__name__
            if hasattr(collection, "get_segments"):
                segments = collection.get_segments()
                if segments:
                    add(kind, {"vertices": np.concatenate(segments),
                               "segment_lengths": [len(segment) for segment in segments]},
                        collection.get_label())
            elif kind != "PathCollection" and hasattr(collection, "get_paths"):
                paths = collection.get_paths()
                if paths:
                    add(kind, {"vertices": np.concatenate([path.vertices for path in paths]),
                               "path_lengths": [len(path.vertices) for path in paths]},
                        collection.get_label())
            if hasattr(collection, "get_offsets"):
                offsets = collection.get_offsets()
                if len(offsets):
                    add(kind, {"offsets": offsets}, collection.get_label())
            if hasattr(collection, "get_array") and collection.get_array() is not None:
                add(kind, {"colors": collection.get_array()}, collection.get_label())
            if hasattr(collection, "get_coordinates"):
                add(kind, {"coordinates": collection.get_coordinates()}, collection.get_label())
        for patch in axis.patches:
            if hasattr(patch, "get_x") and hasattr(patch, "get_width"):
                add("bar", {"x": [patch.get_x()], "width": [patch.get_width()],
                            "y": [patch.get_y()], "height": [patch.get_height()]})
            else:
                panel["unsupported_artists"].append(type(patch).__name__)
        axes.append(panel)
    np.savez_compressed(folder / f"{name}.npz", **arrays)
    sections = source_sections or SOURCE_SECTIONS.get(name)
    if sections is None:
        if name.startswith("behavior_spectrum"):
            sections = ["events", "trials"]
        elif name.startswith(("population", "connectivity", "spike_train")):
            sections = ["spike_train_analysis", "sorted_spikes", "events"]
        elif name.startswith("lfp"):
            sections = ["lfp_analysis"]
        elif name.startswith("spike_field"):
            sections = ["spike_field_analysis"]
        else:
            sections = ["case_studies"]
    manifest = {
        "schema": "neuroephys.figure-data.v1", "figure": name,
        "image": f"../figures/{name}.png", "arrays": f"{name}.npz",
        "source_sections": sections,
        "project_manifest": "../../neuroflow_project.json",
        "raw_recording": str(state.recording_path) if state.recording_path else None,
        "axes": axes,
        "limitation": "Saved numeric Matplotlib artists; text, unsupported patches and upstream transforms require source project and methods review.",
    }
    (folder / f"{name}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
