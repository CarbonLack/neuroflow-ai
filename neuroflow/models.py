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
    recording_path: Path | None = None
    sampling_rate: float = 30_000.0
    channel_count: int = 0
    duration_seconds: float = 0.0
    events: list[dict[str, Any]] = field(default_factory=list)
    ground_truth: dict[int, np.ndarray] = field(default_factory=dict)
    sorted_spikes: dict[int, np.ndarray] = field(default_factory=dict)
    qc: dict[str, Any] = field(default_factory=dict)
    unit_metrics: list[dict[str, Any]] = field(default_factory=list)
    analysis: dict[str, Any] = field(default_factory=dict)
    run_log: list[str] = field(default_factory=list)

    def log(self, text: str) -> None:
        self.run_log.append(text)

    @property
    def ready(self) -> bool:
        return self.recording_path is not None and self.recording_path.exists()
