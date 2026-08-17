from __future__ import annotations

from os import PathLike
from pathlib import Path

from neuroflow.paths import default_workspace, initialize_workspace


def launch(workspace: str | PathLike[str] | None = None) -> int:
    """Launch the NeuroEphys AI desktop interface.

    Install the ``desktop`` extra before calling this function from the Python
    distribution: ``pip install neuroephys-ai[desktop]``.
    """

    root = initialize_workspace(
        Path(workspace) if workspace is not None else default_workspace()
    )
    try:
        from neuroflow.ui import run_app
    except ImportError as exc:
        if exc.name and exc.name.startswith("PySide6"):
            raise RuntimeError(
                "The desktop interface is optional. Install it with "
                "`pip install neuroephys-ai[desktop]`."
            ) from exc
        raise
    return run_app(root)
