from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class WorkflowStep:
    key: str
    title: str
    subtitle: str
    status: str = "pending"
    message: str = "等待运行"


@dataclass
class ProjectState:
    root: Path
    name: str = "Untitled project"
    source_type: str = "unknown"
    source_path: Path | None = None
    recording_path: Path | None = None
    sampling_rate: float = 30_000.0
    channel_count: int = 0
    duration_seconds: float = 0.0
    dtype: str = "int16"
    scale_uv_per_bit: float = 1.0
    electrode_type: str = "generic"
    events: list[dict[str, Any]] = field(default_factory=list)
    trials: list[dict[str, Any]] = field(default_factory=list)
    ground_truth: dict[int, np.ndarray] = field(default_factory=dict)
    sorted_spikes: dict[int, np.ndarray] = field(default_factory=dict)
    sorting_results: dict[str, dict[int, np.ndarray]] = field(default_factory=dict)
    sorting_provenance: dict[str, dict[str, Any]] = field(default_factory=dict)
    active_sorter_key: str | None = None
    sorting_comparison: dict[str, Any] = field(default_factory=dict)
    qc: dict[str, Any] = field(default_factory=dict)
    unit_metrics: list[dict[str, Any]] = field(default_factory=list)
    unit_diagnostics: dict[int, dict[str, Any]] = field(default_factory=dict)
    analysis: dict[str, Any] = field(default_factory=dict)
    spike_train_analysis: dict[str, Any] = field(default_factory=dict)
    lfp_analysis: dict[str, Any] = field(default_factory=dict)
    spike_field_analysis: dict[str, Any] = field(default_factory=dict)
    case_studies: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)
    decoding: dict[str, Any] = field(default_factory=dict)
    regression: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    workflow_status: dict[str, str] = field(default_factory=dict)
    run_log: list[str] = field(default_factory=list)

    def log(self, text: str) -> None:
        self.run_log.append(text)

    @property
    def ready(self) -> bool:
        return self.recording_path is not None and self.recording_path.exists()
