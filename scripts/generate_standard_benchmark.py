from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neuroflow.benchmark import estimate_storage, generate_benchmark
from neuroflow.benchmark.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the NeuroEphys AI standard electrophysiology benchmark")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--tier", choices=("estimate", "lightweight", "full", "all"), default="lightweight")
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.tier == "estimate":
        print(json.dumps(estimate_storage(cfg), ensure_ascii=False, indent=2))
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    log_path = args.output / "generation_log.txt"

    def progress(message: str) -> None:
        line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    tiers = ("lightweight", "full") if args.tier == "all" else (args.tier,)
    result = generate_benchmark(args.output, args.config, tiers, progress)
    progress(f"complete: {len(result['sessions'])} sessions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
