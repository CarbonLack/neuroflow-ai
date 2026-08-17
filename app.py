import sys
from pathlib import Path

from neuroflow.paths import default_workspace, initialize_workspace

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        workspace = initialize_workspace(default_workspace())
    else:
        workspace = Path(__file__).resolve().parent
    if "--self-test-startup" in sys.argv:
        from neuroflow.self_test import run_packaged_startup_self_test

        raise SystemExit(run_packaged_startup_self_test(workspace))
    if "--self-test-kilosort" in sys.argv:
        from neuroflow.self_test import run_packaged_kilosort_self_test

        raise SystemExit(run_packaged_kilosort_self_test(workspace))
    if "--self-test-mountainsort" in sys.argv:
        from neuroflow.self_test import run_packaged_mountainsort_self_test

        raise SystemExit(run_packaged_mountainsort_self_test(workspace))
    if "--self-test-figure-export" in sys.argv:
        from neuroflow.self_test import run_packaged_figure_export_self_test

        raise SystemExit(run_packaged_figure_export_self_test(workspace))
    if "--self-test-internal-sorters" in sys.argv:
        from neuroflow.self_test import run_packaged_internal_sorters_self_test

        raise SystemExit(run_packaged_internal_sorters_self_test(workspace))
    if "--self-test-ai" in sys.argv:
        from neuroflow.self_test import run_packaged_ai_self_test

        raise SystemExit(run_packaged_ai_self_test(workspace))
    from neuroflow.ui import run_app

    raise SystemExit(run_app(workspace))
