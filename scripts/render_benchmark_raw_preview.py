from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neuroflow.figures import raw_overview_figure
from neuroflow.project import load_project


def _densest_window(spikes: dict[int, np.ndarray], duration: float, window_seconds: float) -> float:
    all_times = np.concatenate(list(spikes.values())) if spikes else np.empty(0)
    edges = np.arange(1.0, max(duration - 1.0, 1.0) + window_seconds, window_seconds)
    if len(edges) < 2 or not len(all_times):
        return 2.0
    counts, _ = np.histogram(all_times, bins=edges)
    return float(edges[int(np.argmax(counts))])


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a dense raw benchmark window using the App figure code")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--window-ms", type=int, default=100)
    parser.add_argument("--first-channel", type=int, default=0)
    parser.add_argument("--visible-channels", type=int, default=12)
    args = parser.parse_args()
    state = load_project(args.project)
    with np.load(args.truth) as archive:
        state.ground_truth = {int(key.rsplit("_", 1)[-1]): archive[key] for key in archive.files}
    start = _densest_window(state.ground_truth, state.duration_seconds, args.window_ms / 1000)
    figure = raw_overview_figure(
        state, start_seconds=start, window_ms=args.window_ms,
        first_channel=max(0, args.first_channel),
        visible_channels=min(max(1, args.visible_channels), state.channel_count),
        gain=1.0,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180, bbox_inches="tight")
    plt.close(figure)
    print(f"rendered {args.output} at {start:.3f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
