from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neuroflow.ibl import download_bwm_example, download_bwm_trials_aggregate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download one processed IBL Brain-Wide Map session for NeuroFlow."
    )
    parser.add_argument("--cache", type=Path, default=Path("ibl_cache"))
    parser.add_argument("--eid", help="Optional public IBL experiment UUID")
    parser.add_argument("--probe", help="Optional probe label, e.g. probe00")
    parser.add_argument(
        "--full-session",
        action="store_true",
        help="Download processed trials and spikes through ONE instead of the 24 MB trials aggregate.",
    )
    args = parser.parse_args()
    if args.full_session:
        path = download_bwm_example(
            args.cache,
            eid=args.eid,
            probe=args.probe,
            progress=print,
        )
        print(f"\nImport this ALF folder in NeuroFlow:\n{path}")
    else:
        path = download_bwm_trials_aggregate(args.cache, progress=print)
        print(f"\nImport this IBL aggregate file in NeuroFlow:\n{path}")


if __name__ == "__main__":
    main()
