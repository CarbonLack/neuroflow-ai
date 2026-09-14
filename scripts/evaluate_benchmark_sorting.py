from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neuroflow.benchmark.sorting_evaluator import evaluate_candidate_sorting, write_sorting_evaluation


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Kilosort/Phy-style output with a benchmark ground truth")
    parser.add_argument("--truth", type=Path, required=True, help="Path to true_spike_times.npz")
    parser.add_argument("--candidate", type=Path, required=True, help="Folder containing spike_times.npy and spike_clusters.npy")
    parser.add_argument("--sampling-rate", type=float, default=30_000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tolerance-ms", type=float, default=0.4)
    args = parser.parse_args()
    result = evaluate_candidate_sorting(args.truth, args.candidate, args.sampling_rate, args.tolerance_ms / 1000)
    write_sorting_evaluation(result, args.output)
    print(f"median precision={result['median_precision']:.3f}, recall={result['median_recall']:.3f}, F1={result['median_f1']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
