from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "sphinx"
OUTPUT = ROOT / "docs" / "site"
DOCTREES = ROOT / "docs" / ".build" / "doctrees"


def build(language: str) -> None:
    target = OUTPUT / language
    if target.exists():
        shutil.rmtree(target)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-d",
            str(DOCTREES / language),
            "-b",
            "html",
            str(SOURCE / language),
            str(target),
        ],
        check=True,
    )
    for page in target.glob("*.html"):
        page.write_text("\n".join(line.rstrip() for line in page.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")


def main() -> int:
    from generate_task_manual import build_task_manual
    build_task_manual()
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_sphinx_parameter_reference.py"),
        ],
        check=True,
    )
    build("en")
    build("zh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
