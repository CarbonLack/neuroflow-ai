from __future__ import annotations

from neuroflow.figures import behavior_spectrum_figure, categorical_colors
from neuroflow.models import ProjectState


def test_behavior_spectrum_has_animal_and_behavior_rows_with_time_window(tmp_path):
    state = ProjectState(root=tmp_path, name="session", duration_seconds=20)
    state.events = [
        {"time_seconds": 2, "animal_id": "101", "event_family": "light", "event_phase": "on"},
        {"time_seconds": 4, "animal_id": "101", "event_family": "light", "event_phase": "off"},
        {"time_seconds": 5, "animal_id": "101", "event_family": "poke"},
        {"time_seconds": 6, "animal_id": "102", "event_family": "poke"},
        {"time_seconds": 7, "animal_id": "102", "event_family": "sync", "analysis_role": "synchronization"},
    ]
    animals = behavior_spectrum_figure(state, layout="animals", start_seconds=1, window_seconds=10)
    axis = animals.axes[0]
    assert [label.get_text() for label in axis.get_yticklabels()] == ["101", "102"]
    assert axis.get_xlim() == (1, 11)
    assert len(axis.collections) >= 2  # paired light span and instantaneous events
    behaviors = behavior_spectrum_figure(state, layout="behaviors", animal_id="101")
    assert [label.get_text() for label in behaviors.axes[0].get_yticklabels()] == ["light", "poke"]


def test_large_behavior_palette_does_not_repeat_colors():
    labels = [f"behavior_{index:02d}" for index in range(30)]
    palette = categorical_colors(labels)
    assert list(palette) == labels
    assert len(set(palette.values())) == len(labels)
    assert palette == categorical_colors(labels)
