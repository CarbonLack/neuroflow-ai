from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"


def render_svg(source: Path, target: Path, width: int, height: int) -> None:
    renderer = QSvgRenderer(QByteArray(source.read_bytes()))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {source}")
    image = QImage(QSize(width, height), QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(target)):
        raise RuntimeError(f"Could not save {target}")


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication([])
    render_svg(
        BRAND / "neuroephys-ai-mark.svg",
        BRAND / "neuroephys-ai-mark.png",
        512,
        512,
    )
    icon = QIcon(str(BRAND / "neuroephys-ai-mark.svg"))
    if not icon.pixmap(256, 256).save(str(BRAND / "neuroephys-ai.ico")):
        raise RuntimeError("Could not save application icon")
    for stem in (
        "cover-graphite-cyan",
        "cover-midnight-amber",
        "cover-ink-magenta",
        "cover-ink-magenta-zh",
    ):
        render_svg(BRAND / f"{stem}.svg", BRAND / f"{stem}.png", 1920, 1080)
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
