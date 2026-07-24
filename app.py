from pathlib import Path

from neuroflow.ui import run_app


if __name__ == "__main__":
    raise SystemExit(run_app(Path(__file__).resolve().parent))
