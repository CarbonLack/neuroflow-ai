from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from jsonschema import Draft202012Validator

from .models import ProjectState


class AIMode(StrEnum):
    MANUAL = "manual"
    ASSISTANT = "assistant"
    COLLABORATIVE = "collaborative"


@dataclass(frozen=True, slots=True)
class AIToolSpec:
    name: str
    stage: str
    description: str
    input_schema: dict[str, Any]
    risk: str = "low"
    confirmation_required: bool = True
    network_transfer: bool = False
    destructive: bool = False

    def provider_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": self.input_schema,
            },
        }


def _object_schema(
    properties: dict[str, Any] | None = None,
    *,
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


TOOL_REGISTRY: dict[str, AIToolSpec] = {
    "inspect_project": AIToolSpec(
        "inspect_project",
        "import",
        "Read the local structured project inventory without loading raw samples.",
        _object_schema(),
        confirmation_required=False,
    ),
    "summarize_recording": AIToolSpec(
        "summarize_recording",
        "import",
        "Summarize recording metadata, acquisition settings and missing metadata.",
        _object_schema(),
        confirmation_required=False,
    ),
    "run_raw_qc": AIToolSpec(
        "run_raw_qc",
        "qc",
        "Compute deterministic raw-signal quality-control metrics and evidence.",
        _object_schema(
            {
                "preview_seconds": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 60,
                }
            }
        ),
    ),
    "preview_preprocessing": AIToolSpec(
        "preview_preprocessing",
        "preprocess",
        "Preview AP preprocessing on a short segment without overwriting raw data.",
        _object_schema(
            {
                "highpass_hz": {"type": "number", "minimum": 0},
                "lowpass_hz": {"type": "number", "exclusiveMinimum": 0},
                "reference": {
                    "type": "string",
                    "enum": ["none", "common_median", "common_average"],
                },
                "preview_seconds": {
                    "type": "number",
                    "minimum": 0.1,
                    "maximum": 30,
                },
            }
        ),
    ),
    "run_sorter": AIToolSpec(
        "run_sorter",
        "sorting",
        "Run an installed spike sorter and preserve its native and normalized outputs.",
        _object_schema(
            {
                "sorter": {
                    "type": "string",
                    "enum": [
                        "kilosort4",
                        "mountainsort5",
                        "spykingcircus2",
                        "tridesclous2",
                        "simple",
                    ],
                },
                "duration_seconds": {
                    "type": ["number", "null"],
                    "minimum": 1,
                },
                "parameters": {"type": "object"},
            },
            required=["sorter"],
        ),
        risk="high",
    ),
    "load_sorting_result": AIToolSpec(
        "load_sorting_result",
        "sorting",
        "Open the local sorting-result chooser and normalize a user-selected result.",
        _object_schema(
            {
                "sorter": {"type": "string"},
            }
        ),
    ),
    "compute_unit_qc": AIToolSpec(
        "compute_unit_qc",
        "unit_qc",
        "Compute common Unit quality metrics and diagnostic evidence.",
        _object_schema(),
    ),
    "import_behavior": AIToolSpec(
        "import_behavior",
        "sync",
        "Open the local behavior and TTL import wizard. The model cannot choose files.",
        _object_schema(),
    ),
    "align_events": AIToolSpec(
        "align_events",
        "sync",
        "Align imported behavior events to recorded TTL anchors.",
        _object_schema(
            {
                "ttl_channel": {"type": "integer", "minimum": 0},
                "sync_on_code": {"type": "integer"},
                "sync_off_code": {"type": "integer"},
            },
            required=["ttl_channel", "sync_on_code", "sync_off_code"],
        ),
    ),
    "generate_psth": AIToolSpec(
        "generate_psth",
        "analysis",
        "Generate event-aligned raster, PSTH and population summaries.",
        _object_schema(
            {
                "event_codes": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 1,
                    "maxItems": 12,
                    "uniqueItems": True,
                },
                "window_start_s": {"type": "number", "maximum": 0},
                "window_end_s": {"type": "number", "minimum": 0},
                "bin_size_s": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "maximum": 1,
                },
                "baseline_start_s": {"type": "number"},
                "baseline_end_s": {"type": "number"},
            },
            required=[
                "event_codes",
                "window_start_s",
                "window_end_s",
                "bin_size_s",
                "baseline_start_s",
                "baseline_end_s",
            ],
        ),
    ),
    "run_statistics": AIToolSpec(
        "run_statistics",
        "statistics",
        "Run a registered statistical analysis on existing derived measurements.",
        _object_schema(
            {
                "method": {
                    "type": "string",
                    "enum": [
                        "permutation",
                        "mann_whitney",
                        "wilcoxon",
                        "mixed_effects",
                    ],
                },
                "alpha": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "exclusiveMaximum": 1,
                },
                "multiple_comparison": {
                    "type": "string",
                    "enum": ["none", "bh_fdr", "holm"],
                },
            },
            required=["method", "alpha", "multiple_comparison"],
        ),
    ),
    "run_decoding": AIToolSpec(
        "run_decoding",
        "decoding",
        "Run a registered decoder with grouped validation and permutation controls.",
        _object_schema(
            {
                "model": {
                    "type": "string",
                    "enum": [
                        "Logistic regression",
                        "Linear SVM",
                        "Random forest",
                        "XGBoost",
                    ],
                },
                "cv_folds": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 20,
                },
                "permutations": {
                    "type": "integer",
                    "minimum": 20,
                    "maximum": 5000,
                },
            },
            required=["model", "cv_folds", "permutations"],
        ),
        risk="medium",
    ),
    "edit_figure": AIToolSpec(
        "edit_figure",
        "export",
        "Open the local figure editor for a selected figure; no source result is changed.",
        _object_schema(
            {
                "figure_id": {"type": "string"},
            },
            required=["figure_id"],
        ),
    ),
    "export_project": AIToolSpec(
        "export_project",
        "export",
        "Export figures, tables, Methods, provenance and the project manifest.",
        _object_schema(
            {
                "formats": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["png", "svg", "csv", "json", "markdown"],
                    },
                    "minItems": 1,
                    "uniqueItems": True,
                }
            },
            required=["formats"],
        ),
        risk="medium",
    ),
}


@dataclass(slots=True)
class ToolValidation:
    valid: bool
    errors: list[str]
    warnings: list[str]
    spec: AIToolSpec | None = None


def provider_tools() -> list[dict[str, Any]]:
    return [spec.provider_schema() for spec in TOOL_REGISTRY.values()]


def validate_tool_call(
    name: str,
    arguments: dict[str, Any],
    state: ProjectState | None,
    mode: AIMode | str,
) -> ToolValidation:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        normalized_mode = AIMode(str(mode))
    except ValueError:
        normalized_mode = AIMode.MANUAL
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return ToolValidation(False, [f"Unregistered AI tool: {name}"], [], None)
    if normalized_mode != AIMode.COLLABORATIVE:
        errors.append(
            "AI tool execution is available only in collaborative mode."
        )
    for problem in Draft202012Validator(spec.input_schema).iter_errors(
        arguments
    ):
        location = ".".join(str(item) for item in problem.absolute_path)
        errors.append(f"{location or 'arguments'}: {problem.message}")
    if name not in {"inspect_project", "summarize_recording"} and state is None:
        errors.append("Open a project before using this tool.")
        return ToolValidation(not errors, errors, warnings, spec)
    if state is None:
        return ToolValidation(not errors, errors, warnings, spec)

    raw_required = {
        "run_raw_qc",
        "preview_preprocessing",
        "run_sorter",
    }
    if name in raw_required and not state.ready:
        errors.append("This tool requires readable raw voltage.")
    sorting_required = {
        "compute_unit_qc",
        "generate_psth",
        "run_statistics",
        "run_decoding",
    }
    if name in sorting_required and not state.sorted_spikes:
        errors.append("This tool requires an active sorting result.")
    if name in {"align_events", "generate_psth", "run_statistics", "run_decoding"}:
        if not state.events:
            errors.append("No behavior or event data are available.")
    if name == "generate_psth":
        available = {
            int(event.get("event_code", event.get("code", -1)))
            for event in state.events
            if event.get("event_code", event.get("code")) is not None
        }
        requested = set(arguments.get("event_codes", []))
        missing = sorted(requested - available)
        if missing:
            errors.append(f"Requested event codes are absent: {missing}")
        if (
            float(arguments.get("baseline_start_s", -1))
            >= float(arguments.get("baseline_end_s", 0))
        ):
            errors.append("Baseline start must be earlier than baseline end.")
        if (
            float(arguments.get("window_start_s", -1))
            >= float(arguments.get("window_end_s", 1))
        ):
            errors.append("Analysis window start must be earlier than its end.")
    if name == "run_sorter" and arguments.get("sorter") == "kilosort4":
        warnings.append(
            "Kilosort is a high-cost task. Confirm duration, channels, probe "
            "assumptions and result-directory policy before running."
        )
    if name == "run_sorter" and arguments.get("duration_seconds") is not None:
        requested_duration = float(arguments["duration_seconds"])
        if abs(requested_duration - state.duration_seconds) > max(
            1.0,
            state.duration_seconds * 0.001,
        ):
            errors.append(
                "The requested sorter duration differs from the current project "
                "segment. Create or import the intended segment first so the "
                "source frames, duration, audit record, and sorter input agree."
            )
    acquisition = {
        **state.metadata.get("acquisition", {}),
        **state.metadata.get("acquisition_preprocessing", {}),
    }
    highpass = acquisition.get("online_highpass_hz")
    if highpass is None:
        highpass = acquisition.get("highpass_hz")
    if highpass is None:
        online_filters = acquisition.get("online_filters", [])
        low_cuts = [
            float(item["low_cut_hz"])
            for item in online_filters
            if isinstance(item, dict) and item.get("low_cut_hz") is not None
        ]
        if low_cuts:
            highpass = min(low_cuts)
    if highpass is not None and float(highpass) >= 100:
        warnings.append(
            f"The saved recording was acquired with a {float(highpass):g} Hz "
            "high-pass. True LFP and spike-field analyses are unavailable."
        )
    if (
        name == "preview_preprocessing"
        and acquisition.get("ap_preprocessed")
    ):
        warnings.append(
            "Acquisition metadata reports existing online AP filtering/reference. "
            "The preview will preserve that signal and will not apply a second "
            "filter or reference."
        )
    return ToolValidation(not errors, errors, warnings, spec)
