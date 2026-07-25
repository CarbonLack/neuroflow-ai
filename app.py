import sys
from pathlib import Path

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        workspace = Path.home() / "Documents" / "NeuroFlow"
    else:
        workspace = Path(__file__).resolve().parent
    if "--self-test-kilosort" in sys.argv:
        from neuroflow.self_test import run_packaged_kilosort_self_test

        raise SystemExit(run_packaged_kilosort_self_test(workspace))
    from neuroflow.ui import run_app

    raise SystemExit(run_app(workspace))
