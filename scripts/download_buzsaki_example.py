from __future__ import annotations

import argparse
import shutil
import urllib.request
from pathlib import Path

DANDISET = "000552"
VERSION = "0.230630.2304"
ASSET_ID = "f36a3ffe-1aa2-4019-a8fc-07b03bb2b38e"
FILENAME = "sub-e14-2m3_ses-e14-2m3-201121_behavior+ecephys.nwb"
DOWNLOAD_URL = (
    "https://api.dandiarchive.org/api/dandisets/"
    f"{DANDISET}/versions/{VERSION}/assets/{ASSET_ID}/download/"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download the fixed Buzsáki/DANDI NWB validation asset used by NeuroFlow."
        )
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path.home()
        / "Documents"
        / "NeuroFlow"
        / "PublicValidation"
        / "Buzsaki"
        / f"DANDI_{DANDISET}",
    )
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    target = args.cache / FILENAME
    if target.exists() and target.stat().st_size > 40_000_000:
        print(f"Already cached: {target}")
        return
    partial = target.with_suffix(".nwb.partial")
    request = urllib.request.Request(
        DOWNLOAD_URL,
        headers={"User-Agent": "NeuroFlow public-data validator"},
    )
    print(
        f"Downloading DANDI {DANDISET}/{VERSION}, asset {ASSET_ID}\n"
        f"Destination: {target}"
    )
    with urllib.request.urlopen(request) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    partial.replace(target)
    print(
        f"Ready: {target}\n"
        "In NeuroFlow choose Public validation data → DANDI / Buzsáki NWB."
    )


if __name__ == "__main__":
    main()
