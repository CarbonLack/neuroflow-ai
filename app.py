import sys
from pathlib import Path

from neuroflow.ui import run_app

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        workspace = Path.home() / "Documents" / "NeuroFlow"
    else:
        workspace = Path(__file__).resolve().parent
    raise SystemExit(run_app(workspace))
