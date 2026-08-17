from __future__ import annotations

import os
from pathlib import Path

from .product import LEGACY_PROJECT_NAME


def default_workspace() -> Path:
    """Return the writable user workspace used by the desktop application.

    ``NEUROEPHYS_HOME`` provides an explicit override for managed laboratory
    computers and automated tests. Existing NeuroFlow users keep their legacy
    workspace until they choose to migrate it.
    """

    override = os.environ.get("NEUROEPHYS_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    documents = Path.home() / "Documents"
    preferred = documents / "NeuroEphysAI"
    legacy = documents / LEGACY_PROJECT_NAME
    if legacy.exists() and not preferred.exists():
        return legacy
    return preferred


def initialize_workspace(workspace: Path | None = None) -> Path:
    """Create the stable writable directory layout for a local installation."""

    root = (workspace or default_workspace()).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ("projects", "DemoData", "cache", "logs"):
        (root / name).mkdir(exist_ok=True)
    return root
