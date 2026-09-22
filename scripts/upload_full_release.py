"""Upload a validated Full installer to an existing GitHub release.

Uses the workstation's Git credential helper in memory. It never prints or
stores the token and never deletes/replaces an existing release asset.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import requests


OWNER = "CarbonLack"
REPOSITORY = "neuroflow-ai"
API = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}"


def credential_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token
    result = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("GitHub credential helper could not provide an upload token")
    for line in result.stdout.splitlines():
        if line.startswith("password="):
            return line.partition("=")[2]
    raise RuntimeError("No GitHub token found in the credential helper")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    expected_name = f"NeuroEphysAI-Setup-{args.version}-Full.exe"
    path = args.file.resolve()
    if path.name != expected_name or not path.is_file():
        raise ValueError(f"Expected an existing validated {expected_name}")
    if path.stat().st_size >= 2_147_483_648:
        raise ValueError("GitHub release assets have a 2 GiB per-file limit")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {credential_token()}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "NeuroEphysAI-Release-Uploader",
    }
    release_response = requests.get(
        f"{API}/releases/tags/v{args.version}", headers=headers, timeout=30
    )
    release_response.raise_for_status()
    release = release_response.json()
    for asset in release.get("assets", []):
        if asset.get("name") != expected_name:
            continue
        if int(asset.get("size", -1)) != path.stat().st_size:
            raise RuntimeError("A different-sized Full installer already exists online; refusing to overwrite")
        local_digest = sha256(path)
        remote_digest = str(asset.get("digest") or "")
        if remote_digest and remote_digest != f"sha256:{local_digest}":
            raise RuntimeError("The existing online Full installer has a different SHA-256")
        print(f"Already uploaded and size verified: {asset['browser_download_url']}")
        return
    upload_url = (
        f"https://uploads.github.com/repos/{OWNER}/{REPOSITORY}/releases/"
        f"{release['id']}/assets?name={quote(expected_name)}"
    )
    upload_headers = {
        **headers,
        "Content-Type": "application/octet-stream",
        "Content-Length": str(path.stat().st_size),
    }
    with path.open("rb") as stream:
        response = requests.post(
            upload_url, headers=upload_headers, data=stream, timeout=(30, 3600)
        )
    response.raise_for_status()
    asset = response.json()
    if int(asset.get("size", -1)) != path.stat().st_size:
        raise RuntimeError("GitHub reported a different upload size")
    local_digest = sha256(path)
    remote_digest = str(asset.get("digest") or "")
    if remote_digest and remote_digest != f"sha256:{local_digest}":
        raise RuntimeError("GitHub reported a different upload SHA-256")
    print(f"Uploaded and verified Full installer: {asset['browser_download_url']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Upload failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
