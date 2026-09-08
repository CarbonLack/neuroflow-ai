"""Small reusable desktop layout and monochrome icon primitives."""
from PySide6.QtCore import QByteArray, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLayout


class FlowLayout(QLayout):
    """Wrap complete controls instead of forcing the analysis page wider."""
    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self.items = []
        self.setSpacing(spacing)
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self.items.append(item)

    def addStretch(self, *_):
        pass

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._arrange(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrange(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            if not item.isEmpty():
                size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _arrange(self, rect, measure):
        margins = self.contentsMargins()
        area = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x, y, row_height = area.x(), area.y(), 0
        for item in self.items:
            if item.isEmpty():
                continue
            size = item.sizeHint()
            size.setWidth(min(size.width(), area.width()))
            if x + size.width() > area.right() + 1 and row_height:
                x = area.x()
                y += row_height + self.spacing()
                row_height = 0
            if not measure:
                item.setGeometry(QRect(QPoint(x, y), size))
            x += size.width() + self.spacing()
            row_height = max(row_height, size.height())
        return y + row_height - rect.y() + margins.bottom()


_PATHS = {
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "folder": '<path d="M3 7h6l2 2h10l-2 11H3zM3 7V4h6l2 3h8v2"/>',
    "home": '<path d="m3 11 9-8 9 8M5 10v11h5v-7h4v7h5V10"/>',
    "save": '<path d="M4 3h13l3 3v15H4zM8 3v6h8V3M8 21v-7h8v7"/>',
    "play": '<path d="m7 4 13 8-13 8z"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4M12 17h.01"/>',
    "book": '<path d="M3 4h6l3 2 3-2h6v16h-6l-3 2-3-2H3zM12 6v16"/>',
    "chat": '<path d="M3 4h18v13H9l-6 4z"/><path d="M7 8h10M7 12h7"/>',
    "settings": '<path d="M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6"/>',
    "expand": '<path d="M9 3H3v6M15 3h6v6M3 15v6h6M21 15v6h-6"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "send": '<path d="m3 3 18 9-18 9 3-9zM6 12h15"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
}


def line_icon(name, color="#ded4e5"):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{_PATHS[name]}</svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
