"""Native Qt chat bubbles shared by the compact sidebar and expanded assistant."""
from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QTextBrowser,
    QVBoxLayout, QWidget,
)


class BubbleChatView(QScrollArea):
    """A real two-sided bubble layout, not HTML CSS that Qt silently ignores."""

    anchorClicked = Signal(QUrl)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(12)
        self._layout.addStretch()
        self.setWidget(self._content)
        self._messages: list[tuple[str, str, QFrame, QTextBrowser]] = []
        self._placeholder = ""

    def clear(self) -> None:
        for _, _, bubble, _ in self._messages:
            self._layout.removeWidget(bubble.parentWidget())
            bubble.parentWidget().deleteLater()
        self._messages.clear()

    def setPlaceholderText(self, text: str) -> None:  # noqa: N802
        self._placeholder = text

    def append_message(self, role: str, label: str, body_html: str) -> None:
        row = QWidget(self._content)
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        bubble = QFrame(row)
        bubble.setObjectName("ChatUserBubble" if role == "user" else "ChatAssistantBubble")
        bubble.setStyleSheet(
            "QFrame#ChatUserBubble {background:#34253e; border:1px solid #a56cba; border-radius:13px;}"
            "QFrame#ChatAssistantBubble {background:#201d2b; border:1px solid #547b6b; border-radius:13px;}"
        )
        contents = QVBoxLayout(bubble)
        contents.setContentsMargins(13, 9, 13, 11)
        contents.setSpacing(5)
        heading = QLabel(label, bubble)
        heading.setStyleSheet(
            "color:#e1b5ed; font-size:11px; font-weight:700; border:none;"
            if role == "user" else
            "color:#a9dfc5; font-size:11px; font-weight:700; border:none;"
        )
        contents.addWidget(heading)
        body = QTextBrowser(bubble)
        body.setOpenExternalLinks(False)
        body.anchorClicked.connect(self.anchorClicked)
        body.setHtml(body_html)
        body.setFrameShape(QFrame.NoFrame)
        body.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        body.setStyleSheet("background:transparent; color:#f5f1fa; border:none;")
        contents.addWidget(body)
        if role == "user":
            line.addStretch(1)
            line.addWidget(bubble, 4)
        else:
            line.addWidget(bubble, 4)
            line.addStretch(1)
        self._layout.insertWidget(self._layout.count() - 1, row)
        self._messages.append((role, label, bubble, body))
        self._resize_bodies()
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _resize_bodies(self) -> None:
        available = max(160, self.viewport().width() - 20)
        for _, _, bubble, body in self._messages:
            # A newly added bubble may still report its tiny pre-layout width.
            # Measuring against that value caused chat text to wrap at ~155 px
            # even when the dialog had hundreds of pixels available.
            bubble_width = max(150, int(available * 0.96))
            bubble.setMaximumWidth(bubble_width)
            width = max(125, bubble_width - 28)
            body.document().setTextWidth(width)
            body.setFixedHeight(max(32, int(body.document().size().height()) + 12))

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        QTimer.singleShot(0, self._resize_bodies)

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def toPlainText(self) -> str:  # noqa: N802 - compatibility with earlier view
        return "\n".join(
            f"{label}\n{body.toPlainText()}" for _, label, _, body in self._messages
        )

    def setHtml(self, html: str) -> None:  # noqa: N802 - simple empty-state compatibility
        self.clear()
        self.append_message("assistant", "NeuroEphys AI", html)

    def toHtml(self) -> str:  # noqa: N802 - read-only test/debug representation
        return "\n".join(body.toHtml() for _, _, _, body in self._messages)


def plain_html(text: str) -> str:
    return escape(text).replace("\n", "<br>")
