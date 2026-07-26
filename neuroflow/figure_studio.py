from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import numpy as np
from matplotlib import colors as mpl_colors
from matplotlib.collections import PathCollection, PolyCollection
from matplotlib.image import AxesImage
from matplotlib.legend import Legend
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text
from matplotlib.ticker import (
    AutoMinorLocator,
    FuncFormatter,
    MultipleLocator,
    NullLocator,
    ScalarFormatter,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


def _rgba_hex(value: Any, fallback: str = "#000000") -> str:
    try:
        return mpl_colors.to_hex(value, keep_alpha=False)
    except (TypeError, ValueError):
        return fallback


def _artist_name(artist: Any, index: int) -> str:
    label = getattr(artist, "get_label", lambda: "")()
    if label and not str(label).startswith("_"):
        return str(label)
    if isinstance(artist, Line2D):
        return f"Line {index}"
    if isinstance(artist, PathCollection):
        return f"Scatter {index}"
    if isinstance(artist, PolyCollection):
        return f"Filled region {index}"
    if isinstance(artist, Patch):
        return f"Patch / bar {index}"
    if isinstance(artist, AxesImage):
        return f"Image / heatmap {index}"
    if isinstance(artist, Text):
        text = artist.get_text().strip().replace("\n", " ")
        return text[:36] or f"Text {index}"
    return f"{type(artist).__name__} {index}"


def figure_artist_catalog(figure) -> list[dict[str, Any]]:
    """Return the editable object hierarchy used by the studio and tests."""
    result: list[dict[str, Any]] = [{"kind": "figure", "name": "Figure", "object": figure}]
    for axis_index, axis in enumerate(figure.axes, start=1):
        title = axis.get_title().strip()
        result.append(
            {
                "kind": "axis",
                "name": title or f"Axis {axis_index}",
                "object": axis,
                "axis_index": axis_index,
            }
        )
        artists: list[Any] = []
        artists.extend(axis.lines)
        artists.extend(axis.collections)
        artists.extend(axis.patches)
        artists.extend(axis.images)
        artists.extend(
            text
            for text in axis.texts
            if text.get_text().strip()
        )
        legend = axis.get_legend()
        if legend is not None:
            artists.append(legend)
        seen: set[int] = set()
        for artist_index, artist in enumerate(artists, start=1):
            if id(artist) in seen:
                continue
            seen.add(id(artist))
            result.append(
                {
                    "kind": "artist",
                    "name": _artist_name(artist, artist_index),
                    "object": artist,
                    "axis_index": axis_index,
                }
            )
    return result


class ColorButton(QPushButton):
    def __init__(self, color: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = _rgba_hex(color)
        self.clicked.connect(self._choose)
        self._refresh()

    def color(self) -> str:
        return self._color

    def set_color(self, value: Any) -> None:
        self._color = _rgba_hex(value)
        self._refresh()

    def _choose(self) -> None:
        selected = QColorDialog.getColor(QColor(self._color), self)
        if selected.isValid():
            self._color = selected.name()
            self._refresh()

    def _refresh(self) -> None:
        foreground = "#ffffff" if QColor(self._color).lightness() < 120 else "#111111"
        self.setText(self._color)
        self.setStyleSheet(
            f"QPushButton {{background: {self._color}; color: {foreground};}}"
        )


@dataclass
class Binding:
    apply: Callable[[], None]


class FigureStudioDialog(QDialog):
    """Object-level Matplotlib editor for publication figure refinement."""

    def __init__(
        self,
        figure,
        language: str = "zh_CN",
        parent: QWidget | None = None,
        initial_axis=None,
    ):
        super().__init__(parent)
        self.figure = figure
        self.language = language
        self.bindings: list[Binding] = []
        self._catalog = figure_artist_catalog(figure)
        self._snapshots = {
            id(item["object"]): self._snapshot(item["object"]) for item in self._catalog
        }
        self.setWindowTitle(
            "Figure Studio - 图中元素编辑器"
            if language == "zh_CN"
            else "Figure Studio - object editor"
        )
        self.resize(1180, 840)
        root = QVBoxLayout(self)

        heading = QLabel(
            "逐个选择并编辑整图、坐标轴、曲线、散点、柱形、热图、文字和图例"
            if language == "zh_CN"
            else "Select and edit the figure, axes, lines, points, patches, images, text, and legends"
        )
        heading.setStyleSheet("font-size: 19px; font-weight: 700;")
        root.addWidget(heading)
        explanation = QLabel(
            (
                "这里修改的是当前图的呈现，不会重新计算数据。左侧选择对象，右侧只显示该对象"
                "真正可用的属性；点击‘应用并预览’后主图立即更新。"
            )
            if language == "zh_CN"
            else (
                "Presentation edits do not recompute data. Select an object on the left, "
                "edit its available properties, and apply to redraw the main figure."
            )
        )
        explanation.setWordWrap(True)
        explanation.setObjectName("Muted")
        root.addWidget(explanation)

        splitter = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["图中对象" if language == "zh_CN" else "Figure objects"]
        )
        self.tree.setMinimumWidth(300)
        self.tree.currentItemChanged.connect(self._selection_changed)
        splitter.addWidget(self.tree)

        editor_container = QWidget()
        editor_outer = QVBoxLayout(editor_container)
        self.target_heading = QLabel()
        self.target_heading.setStyleSheet("font-size: 17px; font-weight: 700;")
        editor_outer.addWidget(self.target_heading)
        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_scroll.setFrameShape(QFrame.NoFrame)
        self.editor_body = QWidget()
        self.editor_layout = QFormLayout(self.editor_body)
        self.editor_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.editor_scroll.setWidget(self.editor_body)
        editor_outer.addWidget(self.editor_scroll, 1)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(230)
        self.preview_label.setStyleSheet(
            "QLabel { background: #ffffff; border: 1px solid #d6dfdc; }"
        )
        editor_outer.addWidget(self.preview_label)
        splitter.addWidget(editor_container)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        action_row = QHBoxLayout()
        self.reset_button = QPushButton(
            "恢复当前对象初始样式" if language == "zh_CN" else "Reset selected object"
        )
        self.reset_button.clicked.connect(self._reset_selected)
        self.apply_button = QPushButton(
            "应用并预览" if language == "zh_CN" else "Apply and preview"
        )
        self.apply_button.setObjectName("Primary")
        self.apply_button.clicked.connect(self._apply)
        self.export_button = QPushButton(
            "按当前样式导出" if language == "zh_CN" else "Export current style..."
        )
        self.export_button.clicked.connect(self._export)
        action_row.addWidget(self.reset_button)
        action_row.addStretch()
        action_row.addWidget(self.export_button)
        action_row.addWidget(self.apply_button)
        root.addLayout(action_row)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        root.addWidget(close)

        self._populate_tree()
        initial_item = self.tree.topLevelItem(0)
        if initial_axis is not None:
            for index in range(self.tree.topLevelItemCount()):
                top = self.tree.topLevelItem(index)
                for child_index in range(top.childCount()):
                    child = top.child(child_index)
                    if child.data(0, Qt.UserRole) is initial_axis:
                        initial_item = child
                        break
        self.tree.setCurrentItem(initial_item)
        self._update_preview()

    def _update_preview(self) -> None:
        """Render the edited figure into the dialog without changing its data."""
        buffer = BytesIO()
        self.figure.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        available = self.preview_label.size()
        if available.width() < 20 or available.height() < 20:
            available.setWidth(760)
            available.setHeight(230)
        self.preview_label.setPixmap(
            pixmap.scaled(
                available,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _populate_tree(self) -> None:
        figure_item = QTreeWidgetItem(
            ["整张图 / Figure" if self.language == "zh_CN" else "Whole figure"]
        )
        figure_item.setData(0, Qt.UserRole, self.figure)
        self.tree.addTopLevelItem(figure_item)
        axis_items: dict[int, QTreeWidgetItem] = {}
        for item in self._catalog[1:]:
            if item["kind"] == "axis":
                axis_item = QTreeWidgetItem(
                    [
                        f"坐标轴 {item['axis_index']} · {item['name']}"
                        if self.language == "zh_CN"
                        else f"Axis {item['axis_index']} · {item['name']}"
                    ]
                )
                axis_item.setData(0, Qt.UserRole, item["object"])
                self.tree.addTopLevelItem(axis_item)
                axis_items[item["axis_index"]] = axis_item
            else:
                child = QTreeWidgetItem([item["name"]])
                child.setData(0, Qt.UserRole, item["object"])
                axis_items[item["axis_index"]].addChild(child)
        self.tree.expandAll()

    def _clear_form(self) -> None:
        while self.editor_layout.rowCount():
            self.editor_layout.removeRow(0)
        self.bindings.clear()

    def _selection_changed(self, current, _previous) -> None:
        self._clear_form()
        if current is None:
            return
        target = current.data(0, Qt.UserRole)
        self.target_heading.setText(current.text(0))
        if target is self.figure:
            self._build_figure_editor()
        elif target in self.figure.axes:
            self._build_axis_editor(target)
        else:
            self._build_artist_editor(target)

    def _double(
        self,
        value: float,
        minimum: float = -1e12,
        maximum: float = 1e12,
        decimals: int = 4,
        step: float = 0.1,
    ) -> QDoubleSpinBox:
        control = QDoubleSpinBox()
        control.setRange(minimum, maximum)
        control.setDecimals(decimals)
        control.setSingleStep(step)
        control.setValue(float(value))
        return control

    def _spin(self, value: int, minimum: int = 1, maximum: int = 10000) -> QSpinBox:
        control = QSpinBox()
        control.setRange(minimum, maximum)
        control.setValue(int(value))
        return control

    def _combo(self, values: list[str], current: str) -> QComboBox:
        control = QComboBox()
        control.addItems(values)
        index = control.findText(str(current))
        control.setCurrentIndex(max(index, 0))
        return control

    def _row(self, zh: str, en: str, widget: QWidget) -> None:
        self.editor_layout.addRow(zh if self.language == "zh_CN" else en, widget)

    def _section(self, zh: str, en: str) -> None:
        label = QLabel(zh if self.language == "zh_CN" else en)
        label.setStyleSheet(
            "font-size: 15px; font-weight: 700; margin-top: 10px; "
            "padding-top: 8px; border-top: 1px solid #d8e0dc;"
        )
        self.editor_layout.addRow(label)

    def _build_figure_editor(self) -> None:
        width, height = self.figure.get_size_inches()
        width_control = self._double(width, 1.0, 30.0, 2, 0.1)
        height_control = self._double(height, 1.0, 30.0, 2, 0.1)
        dpi_control = self._spin(round(self.figure.dpi), 50, 1200)
        face = ColorButton(self.figure.get_facecolor())
        layout_preset = self._combo(
            [
                "Custom",
                "Single column (85 mm)",
                "Double column (178 mm)",
                "Square",
                "Presentation 16:9",
            ],
            "Custom",
        )
        transparent = QCheckBox(
            "导出时使用透明背景" if self.language == "zh_CN" else "Transparent on export"
        )
        self._row("宽度（英寸）", "Width (inches)", width_control)
        self._row("高度（英寸）", "Height (inches)", height_control)
        self._row("显示 / 导出 DPI", "Display / export DPI", dpi_control)
        self._row("背景颜色", "Background color", face)
        self._row("期刊尺寸预设", "Publication size preset", layout_preset)
        self._row("透明背景", "Transparent background", transparent)
        self._export_transparent = transparent

        def apply() -> None:
            width_value, height_value = width_control.value(), height_control.value()
            preset = layout_preset.currentText()
            if preset == "Single column (85 mm)":
                width_value = 85 / 25.4
            elif preset == "Double column (178 mm)":
                width_value = 178 / 25.4
            elif preset == "Square":
                height_value = width_value
            elif preset == "Presentation 16:9":
                height_value = width_value * 9 / 16
            self.figure.set_size_inches(width_value, height_value, forward=True)
            self.figure.set_dpi(dpi_control.value())
            self.figure.set_facecolor(face.color())

        self.bindings.append(Binding(apply))

    def _build_axis_editor(self, axis) -> None:
        self._section("标题、字体与范围", "Titles, type, and ranges")
        title = QLineEdit(axis.get_title())
        xlabel = QLineEdit(axis.get_xlabel())
        ylabel = QLineEdit(axis.get_ylabel())
        title_align = self._combo(["left", "center", "right"], "left")
        title_size = self._double(axis.title.get_fontsize(), 1, 100, 1, 1)
        title_weight = self._combo(
            ["normal", "bold", "medium", "semibold"], axis.title.get_fontweight()
        )
        title_color = ColorButton(axis.title.get_color(), self)
        xlabel_size = self._double(axis.xaxis.label.get_fontsize(), 1, 100, 1, 1)
        ylabel_size = self._double(axis.yaxis.label.get_fontsize(), 1, 100, 1, 1)
        xlabel_pad = self._double(axis.xaxis.labelpad, -50, 100, 1, 1)
        ylabel_pad = self._double(axis.yaxis.labelpad, -50, 100, 1, 1)
        label_color = ColorButton(axis.xaxis.label.get_color(), self)
        xscale = self._combo(["linear", "log", "symlog", "logit"], axis.get_xscale())
        yscale = self._combo(["linear", "log", "symlog", "logit"], axis.get_yscale())
        xmin = self._double(min(axis.get_xlim()))
        xmax = self._double(max(axis.get_xlim()))
        ymin = self._double(min(axis.get_ylim()))
        ymax = self._double(max(axis.get_ylim()))
        invert_x = QCheckBox(
            "从大到小显示" if self.language == "zh_CN" else "Reverse direction"
        )
        invert_x.setChecked(bool(axis.xaxis_inverted()))
        invert_y = QCheckBox(
            "从大到小显示" if self.language == "zh_CN" else "Reverse direction"
        )
        invert_y.setChecked(bool(axis.yaxis_inverted()))
        face = ColorButton(axis.get_facecolor(), self)
        self._row("图标题", "Graph title", title)
        self._row("标题对齐", "Title alignment", title_align)
        self._row("标题字号", "Title font size", title_size)
        self._row("标题字重", "Title weight", title_weight)
        self._row("标题颜色", "Title color", title_color)
        self._row("X 轴标题", "X-axis title", xlabel)
        self._row("Y 轴标题", "Y-axis title", ylabel)
        self._row("X 标题字号", "X-title font size", xlabel_size)
        self._row("Y 标题字号", "Y-title font size", ylabel_size)
        self._row("X 标题间距", "X-title padding", xlabel_pad)
        self._row("Y 标题间距", "Y-title padding", ylabel_pad)
        self._row("轴标题颜色", "Axis-title color", label_color)
        self._row("X 轴尺度", "X scale", xscale)
        self._row("Y 轴尺度", "Y scale", yscale)
        self._row("X 最小值", "X minimum", xmin)
        self._row("X 最大值", "X maximum", xmax)
        self._row("X 方向", "X direction", invert_x)
        self._row("Y 最小值", "Y minimum", ymin)
        self._row("Y 最大值", "Y maximum", ymax)
        self._row("Y 方向", "Y direction", invert_y)
        self._row("绘图区背景", "Plot-area background", face)

        self._section("绘图区位置与轴长", "Plot position and axis lengths")
        figure_width, figure_height = self.figure.get_size_inches()
        left, bottom, width_fraction, height_fraction = axis.get_position().bounds
        plot_width = self._double(
            width_fraction * figure_width, 0.2, 30.0, 3, 0.1
        )
        plot_height = self._double(
            height_fraction * figure_height, 0.2, 30.0, 3, 0.1
        )
        left_percent = self._double(left * 100.0, 0, 95, 2, 0.5)
        bottom_percent = self._double(bottom * 100.0, 0, 95, 2, 0.5)
        aspect = self._combo(
            ["auto", "equal"],
            "auto" if axis.get_aspect() == "auto" else "equal",
        )
        self._row("X 轴实际长度（英寸）", "X-axis length (inches)", plot_width)
        self._row("Y 轴实际长度（英寸）", "Y-axis length (inches)", plot_height)
        self._row("绘图区左边距（%）", "Plot left position (%)", left_percent)
        self._row("绘图区下边距（%）", "Plot bottom position (%)", bottom_percent)
        self._row("数据纵横比", "Data aspect", aspect)

        self._section("四条坐标轴线", "Individual axis lines")
        spine_controls: dict[str, tuple[QCheckBox, ColorButton, QDoubleSpinBox, QDoubleSpinBox]] = {}
        names = {
            "bottom": ("下方 X 轴", "Bottom X axis"),
            "left": ("左侧 Y 轴", "Left Y axis"),
            "top": ("上方边框", "Top frame"),
            "right": ("右侧边框", "Right frame"),
        }
        for spine_name in ("bottom", "left", "top", "right"):
            spine = axis.spines[spine_name]
            visible = QCheckBox(
                "显示" if self.language == "zh_CN" else "Visible"
            )
            visible.setChecked(spine.get_visible())
            color = ColorButton(spine.get_edgecolor(), self)
            width = self._double(spine.get_linewidth(), 0, 15, 2, 0.1)
            position = spine.get_position()
            offset_value = (
                float(position[1])
                if isinstance(position, tuple) and position[0] == "outward"
                else 0.0
            )
            offset = self._double(offset_value, -100, 100, 1, 1)
            holder = QWidget()
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.addWidget(visible)
            holder_layout.addWidget(QLabel("Color" if self.language == "en_US" else "颜色"))
            holder_layout.addWidget(color)
            holder_layout.addWidget(QLabel("Width" if self.language == "en_US" else "线宽"))
            holder_layout.addWidget(width)
            holder_layout.addWidget(QLabel("Offset" if self.language == "en_US" else "外移"))
            holder_layout.addWidget(offset)
            self._row(names[spine_name][0], names[spine_name][1], holder)
            spine_controls[spine_name] = (visible, color, width, offset)

        self._section("主刻度、次刻度与数字", "Major/minor ticks and numbering")
        x_major_interval = QLineEdit()
        y_major_interval = QLineEdit()
        x_major_interval.setPlaceholderText(
            "自动" if self.language == "zh_CN" else "Automatic"
        )
        y_major_interval.setPlaceholderText(
            "自动" if self.language == "zh_CN" else "Automatic"
        )
        x_minor_divisions = self._spin(0, 0, 20)
        y_minor_divisions = self._spin(0, 0, 20)
        tick_direction = self._combo(["out", "in", "inout"], "out")
        major_length = self._double(4.0, 0, 40, 1, 0.5)
        major_width = self._double(0.8, 0, 12, 2, 0.1)
        minor_length = self._double(2.5, 0, 40, 1, 0.5)
        minor_width = self._double(0.6, 0, 12, 2, 0.1)
        tick_size = self._double(
            axis.get_xticklabels()[0].get_fontsize()
            if axis.get_xticklabels()
            else 10,
            1,
            100,
            1,
            1,
        )
        tick_color = ColorButton(
            axis.get_xticklabels()[0].get_color()
            if axis.get_xticklabels()
            else "#333333"
        )
        x_tick_rotation = self._double(
            axis.get_xticklabels()[0].get_rotation()
            if axis.get_xticklabels()
            else 0,
            -360,
            360,
            1,
            5,
        )
        y_tick_rotation = self._double(
            axis.get_yticklabels()[0].get_rotation()
            if axis.get_yticklabels()
            else 0,
            -360,
            360,
            1,
            5,
        )
        tick_pad = self._double(3.5, -20, 80, 1, 0.5)
        show_top_ticks = QCheckBox(
            "显示上方刻度" if self.language == "zh_CN" else "Show top ticks"
        )
        show_right_ticks = QCheckBox(
            "显示右侧刻度" if self.language == "zh_CN" else "Show right ticks"
        )
        x_number_format = self._combo(
            ["automatic", "integer", "1 decimal", "2 decimals", "3 decimals", "scientific"],
            "automatic",
        )
        y_number_format = self._combo(
            ["automatic", "integer", "1 decimal", "2 decimals", "3 decimals", "scientific"],
            "automatic",
        )
        self._row("X 主刻度间隔", "X major interval", x_major_interval)
        self._row("Y 主刻度间隔", "Y major interval", y_major_interval)
        self._row("X 主刻度间分区数", "X minor divisions", x_minor_divisions)
        self._row("Y 主刻度间分区数", "Y minor divisions", y_minor_divisions)
        self._row("刻度方向", "Tick direction", tick_direction)
        self._row("主刻度长度", "Major tick length", major_length)
        self._row("主刻度线宽", "Major tick width", major_width)
        self._row("次刻度长度", "Minor tick length", minor_length)
        self._row("次刻度线宽", "Minor tick width", minor_width)
        self._row("刻度数字字号", "Tick-label font size", tick_size)
        self._row("刻度与数字颜色", "Tick and number color", tick_color)
        self._row("X 数字旋转角", "X-label rotation", x_tick_rotation)
        self._row("Y 数字旋转角", "Y-label rotation", y_tick_rotation)
        self._row("数字离轴距离", "Tick-label padding", tick_pad)
        self._row("上方刻度", "Top ticks", show_top_ticks)
        self._row("右侧刻度", "Right ticks", show_right_ticks)
        self._row("X 数字格式", "X number format", x_number_format)
        self._row("Y 数字格式", "Y number format", y_number_format)

        self._section("X/Y 独立网格线", "Independent X/Y grid lines")
        x_grid_major = QCheckBox(
            "显示" if self.language == "zh_CN" else "Visible"
        )
        y_grid_major = QCheckBox(
            "显示" if self.language == "zh_CN" else "Visible"
        )
        current_grid = any(line.get_visible() for line in axis.get_xgridlines())
        x_grid_major.setChecked(current_grid)
        y_grid_major.setChecked(
            any(line.get_visible() for line in axis.get_ygridlines())
        )
        x_grid_minor = QCheckBox(
            "显示" if self.language == "zh_CN" else "Visible"
        )
        y_grid_minor = QCheckBox(
            "显示" if self.language == "zh_CN" else "Visible"
        )
        grid_color = ColorButton(
            axis.get_xgridlines()[0].get_color()
            if axis.get_xgridlines()
            else "#d8e0dc"
        )
        grid_alpha = self._double(0.65, 0, 1, 2, 0.05)
        major_grid_width = self._double(0.8, 0, 10, 2, 0.1)
        minor_grid_width = self._double(0.5, 0, 10, 2, 0.1)
        major_grid_style = self._combo(["-", "--", "-.", ":"], "--")
        minor_grid_style = self._combo(["-", "--", "-.", ":"], ":")
        grid_layer = self._combo(["below data", "above data"], "below data")
        self._row("X 主网格", "X major grid", x_grid_major)
        self._row("Y 主网格", "Y major grid", y_grid_major)
        self._row("X 次网格", "X minor grid", x_grid_minor)
        self._row("Y 次网格", "Y minor grid", y_grid_minor)
        self._row("网格颜色", "Grid color", grid_color)
        self._row("网格透明度", "Grid alpha", grid_alpha)
        self._row("主网格线宽", "Major grid width", major_grid_width)
        self._row("次网格线宽", "Minor grid width", minor_grid_width)
        self._row("主网格线型", "Major grid style", major_grid_style)
        self._row("次网格线型", "Minor grid style", minor_grid_style)
        self._row("网格图层", "Grid layer", grid_layer)

        self._section("自定义参考线", "Custom reference lines")
        x_reference = QLineEdit()
        y_reference = QLineEdit()
        x_reference.setPlaceholderText("0, 1.5, 3" if self.language == "en_US" else "例如：0, 1.5, 3")
        y_reference.setPlaceholderText("0, 50" if self.language == "en_US" else "例如：0, 50")
        reference_color = ColorButton("#b34f36", self)
        reference_style = self._combo(["-", "--", "-.", ":"], "--")
        reference_width = self._double(1.0, 0, 10, 2, 0.1)
        reference_alpha = self._double(0.8, 0, 1, 2, 0.05)
        self._row("垂直参考线 X 值", "Vertical lines at X", x_reference)
        self._row("水平参考线 Y 值", "Horizontal lines at Y", y_reference)
        self._row("参考线颜色", "Reference-line color", reference_color)
        self._row("参考线线型", "Reference-line style", reference_style)
        self._row("参考线线宽", "Reference-line width", reference_width)
        self._row("参考线透明度", "Reference-line alpha", reference_alpha)

        self._section("图例", "Legend")
        legend = axis.get_legend()
        legend_visible = QCheckBox(
            "显示图例" if self.language == "zh_CN" else "Show legend"
        )
        legend_visible.setChecked(legend is not None and legend.get_visible())
        legend_title = QLineEdit(legend.get_title().get_text() if legend else "")
        legend_location = self._combo(
            [
                "best",
                "upper right",
                "upper left",
                "lower left",
                "lower right",
                "center left",
                "center right",
                "lower center",
                "upper center",
                "center",
            ],
            "best",
        )
        legend_columns = self._spin(
            getattr(legend, "_ncols", 1) if legend is not None else 1, 1, 12
        )
        legend_font = self._double(
            legend.get_texts()[0].get_fontsize()
            if legend is not None and legend.get_texts()
            else 10,
            1,
            100,
            1,
            1,
        )
        legend_frame = QCheckBox(
            "显示边框" if self.language == "zh_CN" else "Show frame"
        )
        legend_frame.setChecked(legend.get_frame_on() if legend is not None else False)
        legend_face = ColorButton(
            legend.get_frame().get_facecolor() if legend is not None else "#ffffff",
            self,
        )
        legend_edge = ColorButton(
            legend.get_frame().get_edgecolor() if legend is not None else "#333333",
            self,
        )
        legend_frame_width = self._double(
            legend.get_frame().get_linewidth() if legend is not None else 0.8,
            0,
            10,
            2,
            0.1,
        )
        legend_frame_alpha = self._double(
            legend.get_frame().get_alpha()
            if legend is not None and legend.get_frame().get_alpha() is not None
            else 0.8,
            0,
            1,
            2,
            0.05,
        )
        self._row("图例显示", "Legend visibility", legend_visible)
        self._row("图例标题", "Legend title", legend_title)
        self._row("图例位置", "Legend location", legend_location)
        self._row("图例列数", "Legend columns", legend_columns)
        self._row("图例字号", "Legend font size", legend_font)
        self._row("图例边框", "Legend frame", legend_frame)
        self._row("图例背景", "Legend background", legend_face)
        self._row("图例边框颜色", "Legend edge color", legend_edge)
        self._row("图例边框线宽", "Legend edge width", legend_frame_width)
        self._row("图例背景透明度", "Legend background alpha", legend_frame_alpha)

        def _parse_interval(control: QLineEdit, label: str) -> float | None:
            text = control.text().strip()
            if not text:
                return None
            value = float(text)
            if value <= 0:
                raise ValueError(f"{label} must be greater than zero")
            return value

        def _parse_reference_values(control: QLineEdit) -> list[float]:
            text = control.text().strip()
            if not text:
                return []
            return [float(value.strip()) for value in text.split(",") if value.strip()]

        def _formatter(name: str):
            if name == "automatic":
                return ScalarFormatter()
            if name == "scientific":
                formatter = ScalarFormatter(useMathText=True)
                formatter.set_scientific(True)
                formatter.set_powerlimits((-3, 4))
                return formatter
            decimals = {
                "integer": 0,
                "1 decimal": 1,
                "2 decimals": 2,
                "3 decimals": 3,
            }[name]
            return FuncFormatter(lambda value, _position: f"{value:.{decimals}f}")

        def apply() -> None:
            if xmin.value() >= xmax.value() or ymin.value() >= ymax.value():
                raise ValueError(
                    "坐标最小值必须小于最大值"
                    if self.language == "zh_CN"
                    else "Axis minimum must be smaller than maximum"
                )
            figure_width_value, figure_height_value = self.figure.get_size_inches()
            width_fraction_value = plot_width.value() / figure_width_value
            height_fraction_value = plot_height.value() / figure_height_value
            left_value = left_percent.value() / 100.0
            bottom_value = bottom_percent.value() / 100.0
            if (
                left_value + width_fraction_value > 1.0
                or bottom_value + height_fraction_value > 1.0
            ):
                raise ValueError(
                    "绘图区位置与轴长超出画布；请减小轴长或左/下边距"
                    if self.language == "zh_CN"
                    else "Plot position and axis lengths extend beyond the canvas"
                )
            axis.set_position(
                [left_value, bottom_value, width_fraction_value, height_fraction_value]
            )
            axis.set_aspect(aspect.currentText(), adjustable="box")
            axis.set_title(
                title.text(),
                loc=title_align.currentText(),
                fontsize=title_size.value(),
                fontweight=title_weight.currentText(),
                color=title_color.color(),
            )
            axis.set_xlabel(
                xlabel.text(),
                fontsize=xlabel_size.value(),
                labelpad=xlabel_pad.value(),
                color=label_color.color(),
            )
            axis.set_ylabel(
                ylabel.text(),
                fontsize=ylabel_size.value(),
                labelpad=ylabel_pad.value(),
                color=label_color.color(),
            )
            axis.set_xscale(xscale.currentText())
            axis.set_yscale(yscale.currentText())
            axis.set_xlim(xmin.value(), xmax.value())
            axis.set_ylim(ymin.value(), ymax.value())
            axis.xaxis.set_inverted(invert_x.isChecked())
            axis.yaxis.set_inverted(invert_y.isChecked())
            axis.set_facecolor(face.color())

            for spine_name, controls in spine_controls.items():
                visible, color, width, offset = controls
                spine = axis.spines[spine_name]
                spine.set_visible(visible.isChecked())
                spine.set_color(color.color())
                spine.set_linewidth(width.value())
                spine.set_position(("outward", offset.value()))

            x_interval = _parse_interval(x_major_interval, "X major interval")
            y_interval = _parse_interval(y_major_interval, "Y major interval")
            if x_interval is not None:
                axis.xaxis.set_major_locator(MultipleLocator(x_interval))
            if y_interval is not None:
                axis.yaxis.set_major_locator(MultipleLocator(y_interval))
            if x_minor_divisions.value() > 0:
                axis.xaxis.set_minor_locator(
                    AutoMinorLocator(x_minor_divisions.value())
                )
            else:
                axis.xaxis.set_minor_locator(NullLocator())
            if y_minor_divisions.value() > 0:
                axis.yaxis.set_minor_locator(
                    AutoMinorLocator(y_minor_divisions.value())
                )
            else:
                axis.yaxis.set_minor_locator(NullLocator())
            axis.tick_params(
                axis="both",
                which="major",
                direction=tick_direction.currentText(),
                colors=tick_color.color(),
                labelsize=tick_size.value(),
                length=major_length.value(),
                width=major_width.value(),
                pad=tick_pad.value(),
                top=show_top_ticks.isChecked(),
                right=show_right_ticks.isChecked(),
            )
            axis.tick_params(
                axis="both",
                which="minor",
                direction=tick_direction.currentText(),
                colors=tick_color.color(),
                length=minor_length.value(),
                width=minor_width.value(),
                top=show_top_ticks.isChecked(),
                right=show_right_ticks.isChecked(),
            )
            axis.tick_params(axis="x", labelrotation=x_tick_rotation.value())
            axis.tick_params(axis="y", labelrotation=y_tick_rotation.value())
            axis.xaxis.set_major_formatter(_formatter(x_number_format.currentText()))
            axis.yaxis.set_major_formatter(_formatter(y_number_format.currentText()))

            axis.set_axisbelow(grid_layer.currentText() == "below data")
            for grid_axis, which, enabled, width, style in (
                ("x", "major", x_grid_major, major_grid_width, major_grid_style),
                ("y", "major", y_grid_major, major_grid_width, major_grid_style),
                ("x", "minor", x_grid_minor, minor_grid_width, minor_grid_style),
                ("y", "minor", y_grid_minor, minor_grid_width, minor_grid_style),
            ):
                axis.grid(
                    enabled.isChecked(),
                    axis=grid_axis,
                    which=which,
                    color=grid_color.color(),
                    alpha=grid_alpha.value(),
                    linewidth=width.value(),
                    linestyle=style.currentText(),
                )

            for line in tuple(axis.lines):
                gid = line.get_gid()
                if gid and str(gid).startswith("neuroflow-reference-grid:"):
                    line.remove()
            for value in _parse_reference_values(x_reference):
                line = axis.axvline(
                    value,
                    color=reference_color.color(),
                    linestyle=reference_style.currentText(),
                    linewidth=reference_width.value(),
                    alpha=reference_alpha.value(),
                    zorder=1.5,
                )
                line.set_gid(f"neuroflow-reference-grid:x:{value}")
            for value in _parse_reference_values(y_reference):
                line = axis.axhline(
                    value,
                    color=reference_color.color(),
                    linestyle=reference_style.currentText(),
                    linewidth=reference_width.value(),
                    alpha=reference_alpha.value(),
                    zorder=1.5,
                )
                line.set_gid(f"neuroflow-reference-grid:y:{value}")

            if legend_visible.isChecked():
                handles, labels = axis.get_legend_handles_labels()
                if handles:
                    updated_legend = axis.legend(
                        handles,
                        labels,
                        title=legend_title.text(),
                        loc=legend_location.currentText(),
                        ncols=legend_columns.value(),
                        fontsize=legend_font.value(),
                        frameon=legend_frame.isChecked(),
                    )
                    frame = updated_legend.get_frame()
                    frame.set_facecolor(legend_face.color())
                    frame.set_edgecolor(legend_edge.color())
                    frame.set_linewidth(legend_frame_width.value())
                    frame.set_alpha(legend_frame_alpha.value())
            elif axis.get_legend() is not None:
                axis.get_legend().set_visible(False)

        self.bindings.append(Binding(apply))

    def _common_artist_controls(self, artist) -> tuple[QCheckBox, QDoubleSpinBox, QDoubleSpinBox]:
        visible = QCheckBox(
            "显示此元素" if self.language == "zh_CN" else "Show this object"
        )
        visible.setChecked(artist.get_visible())
        alpha = self._double(
            artist.get_alpha() if artist.get_alpha() is not None else 1.0,
            0,
            1,
            2,
            0.05,
        )
        zorder = self._double(artist.get_zorder(), -1000, 1000, 1, 1)
        self._row("可见", "Visible", visible)
        self._row("透明度", "Alpha", alpha)
        self._row("图层顺序", "Z-order", zorder)
        return visible, alpha, zorder

    def _build_artist_editor(self, artist) -> None:
        if isinstance(artist, Legend):
            note = QLabel(
                "图例由坐标轴的图例区域统一编辑，可调整位置、列数、字号、边框和可见性。"
                if self.language == "zh_CN"
                else "Edit legend visibility, position, columns, font, and frame on its parent axis."
            )
            note.setWordWrap(True)
            self.editor_layout.addRow(note)
            return
        visible, alpha, zorder = self._common_artist_controls(artist)
        if isinstance(artist, Line2D):
            self._build_line_editor(artist, visible, alpha, zorder)
        elif isinstance(artist, PathCollection):
            self._build_scatter_editor(artist, visible, alpha, zorder)
        elif isinstance(artist, AxesImage):
            self._build_image_editor(artist, visible, alpha, zorder)
        elif isinstance(artist, Patch):
            self._build_patch_editor(artist, visible, alpha, zorder)
        elif isinstance(artist, Text):
            self._build_text_editor(artist, visible, alpha, zorder)
        elif isinstance(artist, PolyCollection):
            self._build_collection_editor(artist, visible, alpha, zorder)
        else:
            note = QLabel(
                "此元素当前支持可见性、透明度和图层顺序。"
                if self.language == "zh_CN"
                else "This object currently supports visibility, alpha, and z-order."
            )
            note.setWordWrap(True)
            self.editor_layout.addRow(note)
            self.bindings.append(
                Binding(
                    lambda: (
                        artist.set_visible(visible.isChecked()),
                        artist.set_alpha(alpha.value()),
                        artist.set_zorder(zorder.value()),
                    )
                )
            )

    def _build_line_editor(self, artist, visible, alpha, zorder) -> None:
        label = QLineEdit(artist.get_label())
        color = ColorButton(artist.get_color())
        width = self._double(artist.get_linewidth(), 0, 30, 2, 0.1)
        style = self._combo(["-", "--", "-.", ":", "None"], artist.get_linestyle())
        marker = self._combo(
            ["None", ".", ",", "o", "s", "^", "v", "<", ">", "D", "x", "+", "*", "|", "_"],
            str(artist.get_marker()),
        )
        marker_size = self._double(artist.get_markersize(), 0, 100, 2, 0.5)
        marker_face = ColorButton(
            artist.get_markerfacecolor()
            if artist.get_markerfacecolor() not in {"none", "None"}
            else artist.get_color()
        )
        marker_edge = ColorButton(
            artist.get_markeredgecolor()
            if artist.get_markeredgecolor() not in {"none", "None"}
            else artist.get_color()
        )
        self._row("图例名称", "Legend label", label)
        self._row("线条颜色", "Line color", color)
        self._row("线宽", "Line width", width)
        self._row("线型", "Line style", style)
        self._row("点形状", "Marker", marker)
        self._row("点大小", "Marker size", marker_size)
        self._row("点填充色", "Marker face", marker_face)
        self._row("点边框色", "Marker edge", marker_edge)

        def apply() -> None:
            artist.set_visible(visible.isChecked())
            artist.set_alpha(alpha.value())
            artist.set_zorder(zorder.value())
            artist.set_label(label.text())
            artist.set_color(color.color())
            artist.set_linewidth(width.value())
            artist.set_linestyle(style.currentText())
            artist.set_marker(marker.currentText())
            artist.set_markersize(marker_size.value())
            artist.set_markerfacecolor(marker_face.color())
            artist.set_markeredgecolor(marker_edge.color())

        self.bindings.append(Binding(apply))

    def _build_scatter_editor(self, artist, visible, alpha, zorder) -> None:
        label = QLineEdit(artist.get_label())
        face = ColorButton(
            artist.get_facecolors()[0] if len(artist.get_facecolors()) else "#1f77b4"
        )
        edge = ColorButton(
            artist.get_edgecolors()[0] if len(artist.get_edgecolors()) else "#1f77b4"
        )
        sizes = artist.get_sizes()
        size = self._double(float(np.mean(sizes)) if sizes.size else 20.0, 0, 10000, 2, 1)
        widths = artist.get_linewidths()
        width = self._double(
            float(np.mean(widths)) if len(widths) else 0.8, 0, 30, 2, 0.1
        )
        self._row("图例名称", "Legend label", label)
        self._row("点填充色", "Point face color", face)
        self._row("点边框色", "Point edge color", edge)
        self._row("点面积", "Point area", size)
        self._row("点边框线宽", "Point edge width", width)

        def apply() -> None:
            artist.set_visible(visible.isChecked())
            artist.set_alpha(alpha.value())
            artist.set_zorder(zorder.value())
            artist.set_label(label.text())
            artist.set_facecolor(face.color())
            artist.set_edgecolor(edge.color())
            artist.set_sizes(np.full(max(len(artist.get_offsets()), 1), size.value()))
            artist.set_linewidth(width.value())

        self.bindings.append(Binding(apply))

    def _build_patch_editor(self, artist, visible, alpha, zorder) -> None:
        face = ColorButton(artist.get_facecolor())
        edge = ColorButton(artist.get_edgecolor())
        width = self._double(artist.get_linewidth(), 0, 30, 2, 0.1)
        hatch = self._combo(["None", "/", "\\", "|", "-", "+", "x", "o", "O", ".", "*"], artist.get_hatch() or "None")
        self._row("填充色", "Face color", face)
        self._row("边框色", "Edge color", edge)
        self._row("边框线宽", "Edge width", width)
        self._row("填充纹理", "Hatch", hatch)

        def apply() -> None:
            artist.set_visible(visible.isChecked())
            artist.set_alpha(alpha.value())
            artist.set_zorder(zorder.value())
            artist.set_facecolor(face.color())
            artist.set_edgecolor(edge.color())
            artist.set_linewidth(width.value())
            artist.set_hatch(None if hatch.currentText() == "None" else hatch.currentText())

        self.bindings.append(Binding(apply))

    def _build_collection_editor(self, artist, visible, alpha, zorder) -> None:
        face = ColorButton(
            artist.get_facecolors()[0] if len(artist.get_facecolors()) else "#1f77b4"
        )
        edge = ColorButton(
            artist.get_edgecolors()[0] if len(artist.get_edgecolors()) else "#1f77b4"
        )
        width = self._double(
            float(np.mean(artist.get_linewidths()))
            if len(artist.get_linewidths())
            else 0.8,
            0,
            30,
            2,
            0.1,
        )
        self._row("填充色", "Face color", face)
        self._row("边框色", "Edge color", edge)
        self._row("边框线宽", "Edge width", width)

        def apply() -> None:
            artist.set_visible(visible.isChecked())
            artist.set_alpha(alpha.value())
            artist.set_zorder(zorder.value())
            artist.set_facecolor(face.color())
            artist.set_edgecolor(edge.color())
            artist.set_linewidth(width.value())

        self.bindings.append(Binding(apply))

    def _build_image_editor(self, artist, visible, alpha, zorder) -> None:
        cmap_names = [
            "viridis",
            "plasma",
            "inferno",
            "magma",
            "cividis",
            "coolwarm",
            "RdBu_r",
            "Spectral_r",
            "Greys",
        ]
        cmap = self._combo(cmap_names, artist.get_cmap().name)
        vmin, vmax = artist.get_clim()
        vmin_control = self._double(vmin if vmin is not None else 0.0)
        vmax_control = self._double(vmax if vmax is not None else 1.0)
        interpolation = self._combo(
            ["nearest", "none", "bilinear", "bicubic", "spline16", "hanning"],
            artist.get_interpolation(),
        )
        self._row("色图", "Colormap", cmap)
        self._row("颜色最小值", "Color minimum", vmin_control)
        self._row("颜色最大值", "Color maximum", vmax_control)
        self._row("插值方式", "Interpolation", interpolation)

        def apply() -> None:
            if vmin_control.value() >= vmax_control.value():
                raise ValueError(
                    "颜色最小值必须小于最大值"
                    if self.language == "zh_CN"
                    else "Color minimum must be smaller than maximum"
                )
            artist.set_visible(visible.isChecked())
            artist.set_alpha(alpha.value())
            artist.set_zorder(zorder.value())
            artist.set_cmap(cmap.currentText())
            artist.set_clim(vmin_control.value(), vmax_control.value())
            artist.set_interpolation(interpolation.currentText())

        self.bindings.append(Binding(apply))

    def _build_text_editor(self, artist, visible, alpha, zorder) -> None:
        content = QLineEdit(artist.get_text())
        color = ColorButton(artist.get_color())
        size = self._double(artist.get_fontsize(), 1, 100, 1, 1)
        weight = self._combo(
            ["normal", "bold", "light", "medium", "semibold"], artist.get_fontweight()
        )
        style = self._combo(["normal", "italic", "oblique"], artist.get_fontstyle())
        rotation = self._double(artist.get_rotation(), -360, 360, 1, 5)
        horizontal = self._combo(
            ["left", "center", "right"], artist.get_horizontalalignment()
        )
        vertical = self._combo(
            ["top", "center", "bottom", "baseline", "center_baseline"],
            artist.get_verticalalignment(),
        )
        self._row("文字内容", "Text", content)
        self._row("文字颜色", "Text color", color)
        self._row("字号", "Font size", size)
        self._row("字重", "Font weight", weight)
        self._row("字形", "Font style", style)
        self._row("旋转角", "Rotation", rotation)
        self._row("水平对齐", "Horizontal alignment", horizontal)
        self._row("垂直对齐", "Vertical alignment", vertical)

        def apply() -> None:
            artist.set_visible(visible.isChecked())
            artist.set_alpha(alpha.value())
            artist.set_zorder(zorder.value())
            artist.set_text(content.text())
            artist.set_color(color.color())
            artist.set_fontsize(size.value())
            artist.set_fontweight(weight.currentText())
            artist.set_fontstyle(style.currentText())
            artist.set_rotation(rotation.value())
            artist.set_horizontalalignment(horizontal.currentText())
            artist.set_verticalalignment(vertical.currentText())

        self.bindings.append(Binding(apply))

    def _apply(self) -> None:
        try:
            for binding in self.bindings:
                binding.apply()
            self.figure.canvas.draw_idle()
            self._update_preview()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, self.windowTitle(), str(exc))

    def _snapshot(self, target: Any) -> dict[str, Any]:
        if target is self.figure:
            return {
                "size": tuple(target.get_size_inches()),
                "dpi": target.dpi,
                "facecolor": target.get_facecolor(),
            }
        if target in self.figure.axes:
            return {
                "title": target.get_title(),
                "title_color": target.title.get_color(),
                "title_size": target.title.get_fontsize(),
                "title_weight": target.title.get_fontweight(),
                "xlabel": target.get_xlabel(),
                "ylabel": target.get_ylabel(),
                "xlabel_size": target.xaxis.label.get_fontsize(),
                "ylabel_size": target.yaxis.label.get_fontsize(),
                "xlabel_color": target.xaxis.label.get_color(),
                "ylabel_color": target.yaxis.label.get_color(),
                "xlabel_pad": target.xaxis.labelpad,
                "ylabel_pad": target.yaxis.labelpad,
                "xlim": target.get_xlim(),
                "ylim": target.get_ylim(),
                "xscale": target.get_xscale(),
                "yscale": target.get_yscale(),
                "facecolor": target.get_facecolor(),
                "position": target.get_position().bounds,
                "aspect": target.get_aspect(),
                "axisbelow": target.get_axisbelow(),
                "xmajor_locator": target.xaxis.get_major_locator(),
                "ymajor_locator": target.yaxis.get_major_locator(),
                "xminor_locator": target.xaxis.get_minor_locator(),
                "yminor_locator": target.yaxis.get_minor_locator(),
                "xmajor_formatter": target.xaxis.get_major_formatter(),
                "ymajor_formatter": target.yaxis.get_major_formatter(),
                "spines": {
                    name: {
                        "visible": spine.get_visible(),
                        "color": spine.get_edgecolor(),
                        "width": spine.get_linewidth(),
                        "position": spine.get_position(),
                    }
                    for name, spine in target.spines.items()
                },
            }
        base = {
            "visible": target.get_visible(),
            "alpha": target.get_alpha(),
            "zorder": target.get_zorder(),
        }
        if isinstance(target, Line2D):
            base.update(
                {
                    "label": target.get_label(),
                    "color": target.get_color(),
                    "linewidth": target.get_linewidth(),
                    "linestyle": target.get_linestyle(),
                    "marker": target.get_marker(),
                    "markersize": target.get_markersize(),
                    "markerfacecolor": target.get_markerfacecolor(),
                    "markeredgecolor": target.get_markeredgecolor(),
                }
            )
        elif isinstance(target, PathCollection):
            base.update(
                {
                    "label": target.get_label(),
                    "facecolors": np.asarray(target.get_facecolors()).copy(),
                    "edgecolors": np.asarray(target.get_edgecolors()).copy(),
                    "sizes": np.asarray(target.get_sizes()).copy(),
                    "linewidths": np.asarray(target.get_linewidths()).copy(),
                }
            )
        elif isinstance(target, PolyCollection):
            base.update(
                {
                    "facecolors": np.asarray(target.get_facecolors()).copy(),
                    "edgecolors": np.asarray(target.get_edgecolors()).copy(),
                    "linewidths": np.asarray(target.get_linewidths()).copy(),
                }
            )
        elif isinstance(target, Patch):
            base.update(
                {
                    "facecolor": target.get_facecolor(),
                    "edgecolor": target.get_edgecolor(),
                    "linewidth": target.get_linewidth(),
                    "hatch": target.get_hatch(),
                }
            )
        elif isinstance(target, AxesImage):
            base.update(
                {
                    "cmap": target.get_cmap(),
                    "clim": target.get_clim(),
                    "interpolation": target.get_interpolation(),
                }
            )
        elif isinstance(target, Text):
            base.update(
                {
                    "text": target.get_text(),
                    "color": target.get_color(),
                    "fontsize": target.get_fontsize(),
                    "fontweight": target.get_fontweight(),
                    "fontstyle": target.get_fontstyle(),
                    "rotation": target.get_rotation(),
                    "horizontalalignment": target.get_horizontalalignment(),
                    "verticalalignment": target.get_verticalalignment(),
                }
            )
        return base

    def _reset_selected(self) -> None:
        current = self.tree.currentItem()
        if current is None:
            return
        target = current.data(0, Qt.UserRole)
        snapshot = self._snapshots.get(id(target), {})
        if target is self.figure:
            target.set_size_inches(*snapshot["size"], forward=True)
            target.set_dpi(snapshot["dpi"])
            target.set_facecolor(snapshot["facecolor"])
        elif target in self.figure.axes:
            target.set_title(
                snapshot["title"],
                loc="left",
                color=snapshot["title_color"],
                fontsize=snapshot["title_size"],
                fontweight=snapshot["title_weight"],
            )
            target.set_xlabel(
                snapshot["xlabel"],
                fontsize=snapshot["xlabel_size"],
                color=snapshot["xlabel_color"],
                labelpad=snapshot["xlabel_pad"],
            )
            target.set_ylabel(
                snapshot["ylabel"],
                fontsize=snapshot["ylabel_size"],
                color=snapshot["ylabel_color"],
                labelpad=snapshot["ylabel_pad"],
            )
            target.set_xscale(snapshot["xscale"])
            target.set_yscale(snapshot["yscale"])
            target.set_xlim(*snapshot["xlim"])
            target.set_ylim(*snapshot["ylim"])
            target.set_facecolor(snapshot["facecolor"])
            target.set_position(snapshot["position"])
            target.set_aspect(snapshot["aspect"], adjustable="box")
            target.set_axisbelow(snapshot["axisbelow"])
            target.xaxis.set_major_locator(snapshot["xmajor_locator"])
            target.yaxis.set_major_locator(snapshot["ymajor_locator"])
            target.xaxis.set_minor_locator(snapshot["xminor_locator"])
            target.yaxis.set_minor_locator(snapshot["yminor_locator"])
            target.xaxis.set_major_formatter(snapshot["xmajor_formatter"])
            target.yaxis.set_major_formatter(snapshot["ymajor_formatter"])
            for name, values in snapshot["spines"].items():
                spine = target.spines[name]
                spine.set_visible(values["visible"])
                spine.set_color(values["color"])
                spine.set_linewidth(values["width"])
                spine.set_position(values["position"])
            for line in tuple(target.lines):
                gid = line.get_gid()
                if gid and str(gid).startswith("neuroflow-reference-grid:"):
                    line.remove()
        else:
            target.set_visible(snapshot.get("visible", True))
            target.set_alpha(snapshot.get("alpha"))
            target.set_zorder(snapshot.get("zorder", target.get_zorder()))
            if isinstance(target, Line2D):
                target.set_label(snapshot["label"])
                target.set_color(snapshot["color"])
                target.set_linewidth(snapshot["linewidth"])
                target.set_linestyle(snapshot["linestyle"])
                target.set_marker(snapshot["marker"])
                target.set_markersize(snapshot["markersize"])
                target.set_markerfacecolor(snapshot["markerfacecolor"])
                target.set_markeredgecolor(snapshot["markeredgecolor"])
            elif isinstance(target, PathCollection):
                target.set_label(snapshot["label"])
                target.set_facecolors(snapshot["facecolors"])
                target.set_edgecolors(snapshot["edgecolors"])
                target.set_sizes(snapshot["sizes"])
                target.set_linewidths(snapshot["linewidths"])
            elif isinstance(target, PolyCollection):
                target.set_facecolors(snapshot["facecolors"])
                target.set_edgecolors(snapshot["edgecolors"])
                target.set_linewidths(snapshot["linewidths"])
            elif isinstance(target, Patch):
                target.set_facecolor(snapshot["facecolor"])
                target.set_edgecolor(snapshot["edgecolor"])
                target.set_linewidth(snapshot["linewidth"])
                target.set_hatch(snapshot["hatch"])
            elif isinstance(target, AxesImage):
                target.set_cmap(snapshot["cmap"])
                target.set_clim(*snapshot["clim"])
                target.set_interpolation(snapshot["interpolation"])
            elif isinstance(target, Text):
                target.set_text(snapshot["text"])
                target.set_color(snapshot["color"])
                target.set_fontsize(snapshot["fontsize"])
                target.set_fontweight(snapshot["fontweight"])
                target.set_fontstyle(snapshot["fontstyle"])
                target.set_rotation(snapshot["rotation"])
                target.set_horizontalalignment(snapshot["horizontalalignment"])
                target.set_verticalalignment(snapshot["verticalalignment"])
        self.figure.canvas.draw_idle()
        self._update_preview()
        self._selection_changed(current, None)

    def _export(self) -> None:
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "导出当前图" if self.language == "zh_CN" else "Export current figure",
            "neuroflow_figure.svg",
            "SVG (*.svg);;PDF (*.pdf);;PNG (*.png);;TIFF (*.tiff)",
        )
        if not selected:
            return
        transparent = getattr(self, "_export_transparent", None)
        self.figure.savefig(
            selected,
            dpi=self.figure.dpi,
            bbox_inches="tight",
            transparent=transparent.isChecked() if transparent is not None else False,
        )
