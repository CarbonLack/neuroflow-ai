"""Upload verified local release artifacts without replacing existing assets."""
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import quote

import requests

from scripts.upload_full_release import API, credential_token, sha256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-id", type=int, required=True)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {credential_token()}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "NeuroEphysAI-Release-Uploader",
    }
    release_response = requests.get(
        f"{API}/releases/{args.release_id}", headers=headers, timeout=30
    )
    release_response.raise_for_status()
    release = release_response.json()
    existing = {asset["name"]: asset for asset in release.get("assets", [])}
    for path in args.files:
        path = path.resolve(strict=True)
        size = path.stat().st_size
        if size >= 2_147_483_648:
            raise ValueError(f"GitHub's 2 GiB asset limit excludes {path.name}")
        digest = sha256(path)
        prior = existing.get(path.name)
        if prior is not None:
            if int(prior["size"]) != size or (
                prior.get("digest") and prior["digest"] != f"sha256:{digest}"
            ):
                raise RuntimeError(f"Online asset differs; refusing replacement: {path.name}")
            print(f"Already verified: {path.name}", flush=True)
            continue
        url = (
            f"https://uploads.github.com/repos/CarbonLack/neuroflow-ai/"
            f"releases/{release['id']}/assets?name={quote(path.name)}"
        )
        with path.open("rb") as stream:
            response = requests.post(
                url,
                headers={**headers, "Content-Type": "application/octet-stream",
                         "Content-Length": str(size)},
                data=stream,
                timeout=(30, 3600),
            )
        response.raise_for_status()
        asset = response.json()
        if int(asset["size"]) != size or (
            asset.get("digest") and asset["digest"] != f"sha256:{digest}"
        ):
            raise RuntimeError(f"Upload checksum or size mismatch: {path.name}")
        print(f"Uploaded and verified: {path.name}", flush=True)


if __name__ == "__main__":
    main()
