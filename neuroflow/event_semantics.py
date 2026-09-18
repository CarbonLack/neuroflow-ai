from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


MISSING_EVENT_LABELS = {"", "unknown", "nan", "none", "null"}


def event_analysis_label(event: dict[str, Any]) -> tuple[str, str]:
    """Return the most informative analysis label and its source field.

    Imported experiments often call the experimental group ``condition`` while
    benchmark/event tables call it ``label`` or ``event_type``.  Treating a
    missing ``condition`` as the literal class ``unknown`` discards valid event
    semantics and makes downstream decoding fail for the wrong reason.
    """

    for field in ("condition", "label", "event_type", "event"):
        value = event.get(field)
        if value is None:
            continue
        label = str(value).strip()
        if label.casefold() not in MISSING_EVENT_LABELS:
            return label, field
    for field in ("event_code", "code"):
        value = event.get(field)
        if value is not None and str(value).strip():
            return f"event_{value}", field
    return "unknown", "missing"


def event_label_diagnostics(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    labels: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for event in events:
        label, source = event_analysis_label(event)
        labels[label] += 1
        sources[source] += 1
    usable = {
        label: count
        for label, count in labels.items()
        if label.casefold() not in MISSING_EVENT_LABELS
    }
    return {
        "label_counts": dict(sorted(labels.items())),
        "usable_label_counts": dict(sorted(usable.items())),
        "label_source_counts": dict(sorted(sources.items())),
        "usable_class_count": len(usable),
        "event_count": sum(labels.values()),
    }
