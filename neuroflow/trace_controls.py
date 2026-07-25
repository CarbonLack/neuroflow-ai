from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
)

from .help_content import control_help


class TraceControls(QFrame):
    changed = Signal()

    def __init__(self, language: str, parent=None):
        super().__init__(parent)
        self.language = language
        self.setObjectName("TraceControls")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)
        self.heading = QLabel()
        self.heading.setObjectName("FieldLabel")
        layout.addWidget(self.heading)

        self.start_label = QLabel()
        self.start = QDoubleSpinBox()
        self.start.setDecimals(3)
        self.start.setRange(0, 0)
        self.start.setSingleStep(0.1)
        self.start.setSuffix(" s")
        self.start.setProperty("neuroflow_help_key", "trace.start")
        self.start.editingFinished.connect(self.changed.emit)

        self.window_label = QLabel()
        self.window = QSpinBox()
        self.window.setRange(10, 5000)
        self.window.setValue(60)
        self.window.setSuffix(" ms")
        self.window.setProperty("neuroflow_help_key", "trace.window")
        self.window.editingFinished.connect(self.changed.emit)

        self.first_label = QLabel()
        self.first_channel = QSpinBox()
        self.first_channel.setRange(0, 0)
        self.first_channel.setProperty("neuroflow_help_key", "trace.channels")
        self.first_channel.valueChanged.connect(self._constrain_count)
        self.first_channel.editingFinished.connect(self.changed.emit)

        self.count_label = QLabel()
        self.channel_count = QSpinBox()
        self.channel_count.setRange(1, 1)
        self.channel_count.setValue(1)
        self.channel_count.setProperty("neuroflow_help_key", "trace.channels")
        self.channel_count.editingFinished.connect(self.changed.emit)

        self.gain_label = QLabel()
        self.gain = QSlider(Qt.Horizontal)
        self.gain.setRange(5, 80)
        self.gain.setValue(10)
        self.gain.setFixedWidth(105)
        self.gain.setProperty("neuroflow_help_key", "trace.gain")
        self.gain.valueChanged.connect(self._update_gain_text)
        self.gain.sliderReleased.connect(self.changed.emit)
        self.gain_value = QLabel("1.0x")
        self.gain_value.setMinimumWidth(38)

        for label, widget in (
            (self.start_label, self.start),
            (self.window_label, self.window),
            (self.first_label, self.first_channel),
            (self.count_label, self.channel_count),
        ):
            layout.addWidget(label)
            layout.addWidget(widget)
        layout.addWidget(self.gain_label)
        layout.addWidget(self.gain)
        layout.addWidget(self.gain_value)
        layout.addStretch()
        self.set_language(language)

    def set_language(self, language: str) -> None:
        self.language = language
        english = language == "en_US"
        self.heading.setText("Trace browser" if english else "多通道波形浏览")
        self.start_label.setText("Start" if english else "起始")
        self.window_label.setText("Window" if english else "窗口")
        self.first_label.setText("First ch." if english else "首通道")
        self.count_label.setText("Visible" if english else "显示数")
        self.gain_label.setText("Gain" if english else "增益")
        for widget in (
            self.start,
            self.window,
            self.first_channel,
            self.channel_count,
            self.gain,
        ):
            key = widget.property("neuroflow_help_key")
            widget.setToolTip(control_help(str(key), language)[1])

    def set_recording(self, duration_seconds: float, channel_count: int) -> None:
        channel_count = max(int(channel_count), 1)
        self.start.setMaximum(max(float(duration_seconds) - 0.01, 0.0))
        self.start.setValue(min(2.0, self.start.maximum()))
        self.first_channel.setMaximum(channel_count - 1)
        self.channel_count.setMaximum(channel_count)
        self.channel_count.setValue(min(12, channel_count))
        self._constrain_count()

    def _constrain_count(self) -> None:
        available = self.first_channel.maximum() + 1 - self.first_channel.value()
        self.channel_count.setMaximum(max(available, 1))
        if self.channel_count.value() > available:
            self.channel_count.setValue(available)

    def _update_gain_text(self) -> None:
        self.gain_value.setText(f"{self.gain_factor():.1f}x")

    def gain_factor(self) -> float:
        return self.gain.value() / 10.0

    def values(self) -> dict:
        return {
            "start_seconds": float(self.start.value()),
            "window_ms": int(self.window.value()),
            "first_channel": int(self.first_channel.value()),
            "visible_channels": int(self.channel_count.value()),
            "gain": self.gain_factor(),
        }

    def help_controls(self) -> list:
        return [
            self.start,
            self.window,
            self.first_channel,
            self.channel_count,
            self.gain,
        ]
