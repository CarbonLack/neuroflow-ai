"""Task-oriented, offline help that uses Qt's supported rich-text subset."""
from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QFont
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QSplitter, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from .tutorial_catalog import TUTORIAL_CATALOG, catalog_text
from .tutorial_details import TUTORIAL_DETAILS, localized_rows


HELP_STYLE = """
QDialog#TutorialCenter { background: #100d17; color: #f2edf5; }
QWidget#HelpNavigation, QWidget#HelpContent { background: #100d17; }
QLabel { color: #f2edf5; background: transparent; }
QLabel#HelpEyebrow, QLabel#HelpCount { color: #b8adc6; font-size: 12px; }
QLabel#HelpTitle { font-size: 23px; font-weight: 600; }
QLineEdit, QComboBox { color: #f2edf5; background: #211d2b; border: 1px solid #50465e;
    border-radius: 6px; padding: 8px; min-height: 20px; }
QListWidget { color: #e9e2ee; background: #181421; border: 1px solid #40374b;
    border-radius: 7px; outline: none; font-size: 13px; }
QListWidget::item { padding: 10px 8px; border-bottom: 1px solid #292332; }
QListWidget::item:selected { background: #483151; color: #ffffff; }
QListWidget::item:hover { background: #292332; }
QTextBrowser { color: #f2edf5; background: #181421; border: 1px solid #40374b;
    border-radius: 7px; padding: 12px; selection-background-color: #654573; }
QTabWidget::pane { border: none; }
QTabBar::tab { color: #b8adc6; background: #100d17; padding: 11px 16px;
    border-bottom: 2px solid #40374b; }
QTabBar::tab:selected { color: #f2edf5; border-bottom: 2px solid #d885e9; }
QPushButton { color: #f2edf5; background: #211d2b; border: 1px solid #50465e;
    border-radius: 6px; padding: 8px 12px; min-height: 20px; }
QPushButton:hover { background: #302637; border-color: #b279c2; }
QPushButton:disabled { color: #82778e; border-color: #393140; }
QPushButton#HelpOpen { color: #100d17; background: #d885e9; border-color: #d885e9;
    font-weight: 600; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus { border: 2px solid #d885e9; }
QSplitter::handle { background: #302637; width: 6px; height: 6px; }
"""

# QTextDocument ignores much modern CSS. Keep all text colors explicit and use
# paragraphs instead of wide HTML tables, grids, or pale background callouts.
HELP_DOCUMENT_STYLE = """
body, p, li, td { color: #f2edf5; font-family: 'Microsoft YaHei', 'Segoe UI'; }
h2 { color: #ead8f0; font-size: 18px; margin-top: 22px; margin-bottom: 8px; }
h3 { color: #ead8f0; font-size: 16px; margin-top: 20px; margin-bottom: 6px; }
p { margin-top: 6px; margin-bottom: 12px; line-height: 150%; }
a { color: #e3a0ef; }
code { color: #e3a0ef; }
.muted { color: #b8adc6; }
"""


def _paragraph(value: str, *, muted: bool = False) -> str:
    style = ' class="muted"' if muted else ''
    return f'<p{style}>{escape(value).replace(chr(10), "<br>")}</p>'


def task_html(item: dict, language: str, section: str = "steps") -> str:
    """Render an action guide without embedding external scripts or images."""
    english = language == "en_US"
    value = lambda field: catalog_text(item, field, language)
    parts: list[str] = []
    if section == "steps":
        parts += [_paragraph(value("summary")),
                  "<h3>" + ("Have ready" if english else "先准备好") + "</h3>",
                  _paragraph(value("prerequisites"))]
        for index, step in enumerate(item["steps"], 1):
            title = catalog_text(step, "title", language)
            parts += [f'<h3><font color="#d885e9">{index:02d}</font>  {escape(title)}</h3>',
                      _paragraph(catalog_text(step, "body", language))]
        parts += ["<h3>" + ("Check the result" if english else "做完后，检查这里") + "</h3>",
                  _paragraph(value("check")),
                  "<h3>" + ("Where it is saved" if english else "结果保存在哪里") + "</h3>",
                  _paragraph(value("output"))]
    elif section == "reference":
        detail = TUTORIAL_DETAILS.get(item.get("page_key"), {})
        parameters = localized_rows(detail, "parameters", language) if detail else []
        parts.append(_paragraph(
            "These are method references. Controls vary by input and sorter; use the settings visible in your workspace."
            if english else "这里解释方法参数。可调整项随数据入口和 sorter 变化；以工作区实际显示的设置为准。",
            muted=True))
        if not parameters:
            parts.append('<h3>' + ('Before you start' if english else '开始前确认') + '</h3>')
            parts.append(_paragraph(value("prerequisites")))
        for row in parameters:
            parts += [f'<h3>{escape(row["name"])}</h3>', _paragraph(row["meaning"]),
                      _paragraph(("Reference value: " if english else "参考值：") + row["default"]),
                      _paragraph(row["recommended"]), _paragraph(row["effect"], muted=True)]
        reference = item.get("reference", "")
        if reference:
            parts.append('<h3>' + ('Method documentation' if english else '方法文档') + '</h3>')
            parts.append(f'<p><a href="{escape(reference, quote=True)}">{escape(reference)}</a></p>')
    else:
        for problem in item.get("troubleshooting", []):
            parts += [f'<h3>{escape(catalog_text(problem, "title", language))}</h3>',
                      _paragraph(catalog_text(problem, "body", language))]
        parts += ["<h3>" + ("Check the result" if english else "完成检查") + "</h3>",
                  _paragraph(value("check"))]
    return '<html><body>' + ''.join(parts) + '</body></html>'


class TutorialDialog(QDialog):
    """Searchable help with optional navigation back to its owning workbench."""

    def __init__(self, initial_key="import", parent=None, language="zh_CN"):
        super().__init__(parent)
        self.language = language
        self.english = language == "en_US"
        self.settings = QSettings("NeuroEphysAI", "NeuroEphysAI")
        self.setObjectName("TutorialCenter")
        self.setWindowTitle("Tutorial center" if self.english else "教程中心")
        self.setStyleSheet(HELP_STYLE)
        self.resize(1060, 740)
        self.setMinimumSize(580, 440)
        self.owner = parent
        while self.owner is not None and not hasattr(self.owner, "_select_step"):
            self.owner = self.owner.parentWidget()
        self.selected_id = initial_key
        self.read_ids = set(str(self.settings.value("help/read_tasks", "")).split(","))
        self.read_ids.discard("")
        self.font_size = int(self.settings.value("help/font_size", 11))
        self.font_size = min(17, max(10, self.font_size))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 16)
        outer.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("NEUROEPHYS AI  /  " + ("FIELD GUIDE" if self.english else "操作手册"))
        title.setObjectName("HelpEyebrow")
        heading.addWidget(title)
        heading.addStretch()
        self.zoom_out = QPushButton("A−")
        self.zoom_in = QPushButton("A+")
        for button, delta in ((self.zoom_out, -1), (self.zoom_in, 1)):
            button.setFixedWidth(46)
            button.setToolTip(("Text size" if self.english else "调整阅读字号"))
            button.clicked.connect(lambda _checked=False, d=delta: self._zoom(d))
            heading.addWidget(button)
        outer.addLayout(heading)
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Search a task, button or file type…  Ctrl+F" if self.english else
            "搜索操作、按钮或文件格式，例如 Kilosort、保存、三栏…  Ctrl+F")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Search tutorials" if self.english else "搜索教程")
        outer.addWidget(self.search)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        nav = QWidget()
        nav.setObjectName("HelpNavigation")
        nav.setMinimumWidth(160)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        self.category = QComboBox()
        self.category.addItem("All tasks" if self.english else "全部操作", "")
        categories = {}
        for item in TUTORIAL_CATALOG:
            categories[item["category"]] = catalog_text(item, "category", language)
        for key, name in categories.items():
            self.category.addItem(name, key)
        self.category.setAccessibleName("Topic" if self.english else "教程分类")
        nav_layout.addWidget(self.category)
        self.list = QListWidget()
        self.list.setWordWrap(True)
        nav_layout.addWidget(self.list, 1)
        self.count_label = QLabel()
        self.count_label.setObjectName("HelpCount")
        nav_layout.addWidget(self.count_label)
        self.splitter.addWidget(nav)
        content = QWidget()
        content.setObjectName("HelpContent")
        content.setMinimumWidth(260)
        right = QVBoxLayout(content)
        right.setContentsMargins(10, 0, 0, 0)
        self.chapter_label = QLabel()
        self.chapter_label.setObjectName("HelpTitle")
        self.chapter_label.setWordWrap(True)
        self.chapter_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        right.addWidget(self.chapter_label)
        self.tabs = QTabWidget()
        self.browsers = []
        for label in (("Steps", "Parameters", "Troubleshooting") if self.english else
                      ("操作步骤", "参数说明", "遇到问题")):
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)
            browser.document().setDefaultStyleSheet(HELP_DOCUMENT_STYLE)
            browser.document().setDocumentMargin(12)
            self.tabs.addTab(browser, label)
            self.browsers.append(browser)
        self.browser = self.browsers[0]
        right.addWidget(self.tabs, 1)
        actions = QHBoxLayout()
        self.mark_read = QPushButton()
        self.mark_read.clicked.connect(self._toggle_read)
        actions.addWidget(self.mark_read)
        actions.addStretch()
        self.open_button = QPushButton("Open in app" if self.english else "打开对应页面")
        self.open_button.setObjectName("HelpOpen")
        self.open_button.clicked.connect(self._navigate)
        actions.addWidget(self.open_button)
        right.addLayout(actions)
        self.splitter.addWidget(content)
        self.splitter.setSizes([250, 750])
        self.splitter.setStretchFactor(1, 1)
        outer.addWidget(self.splitter, 1)
        footer = QHBoxLayout()
        self.manual_button = QPushButton("Web manual ↗" if self.english else "网页版手册 ↗")
        self.manual_button.clicked.connect(self._open_full_manual)
        footer.addWidget(self.manual_button)
        footer.addStretch()
        self.previous_button = QPushButton("← Previous" if self.english else "← 上一项")
        self.next_button = QPushButton("Next →" if self.english else "下一项 →")
        self.previous_button.clicked.connect(lambda: self._move(-1))
        self.next_button.clicked.connect(lambda: self._move(1))
        footer.addWidget(self.previous_button)
        footer.addWidget(self.next_button)
        outer.addLayout(footer)
        self.search.textChanged.connect(self._filter)
        self.category.currentIndexChanged.connect(self._filter)
        self.list.currentRowChanged.connect(self._show)
        self.find_action = QAction(self)
        self.find_action.setShortcut("Ctrl+F")
        self.find_action.triggered.connect(self.search.setFocus)
        self.addAction(self.find_action)
        self._filter()
        self._apply_font()

    def _filter(self, *_args):
        query = self.search.text().casefold().strip().split()
        category = self.category.currentData()
        self.filtered = []
        for item in TUTORIAL_CATALOG:
            haystack = str(item).casefold()
            if (not category or item["category"] == category) and all(word in haystack for word in query):
                self.filtered.append(item)
        self.list.blockSignals(True)
        self.list.clear()
        for item in self.filtered:
            title = catalog_text(item, "title", self.language)
            entry = QListWidgetItem(("✓  " if item["id"] in self.read_ids else "") + title)
            entry.setToolTip(catalog_text(item, "summary", self.language))
            self.list.addItem(entry)
        index = next((i for i, item in enumerate(self.filtered)
                      if item["id"] == self.selected_id), 0)
        self.list.setCurrentRow(index if self.filtered else -1)
        self.list.blockSignals(False)
        self.count_label.setText(
            f"{len(self.filtered)} tasks · {len(self.read_ids)} read" if self.english else
            f"{len(self.filtered)} 项操作 · 已读 {len(self.read_ids)} 项")
        self._show(index if self.filtered else -1)

    def _show(self, index):
        valid = 0 <= index < len(self.filtered)
        self.open_button.setEnabled(valid and self.owner is not None)
        self.mark_read.setEnabled(valid)
        self.previous_button.setEnabled(valid and index > 0)
        self.next_button.setEnabled(valid and index < len(self.filtered) - 1)
        if not valid:
            self.chapter_label.setText("No matching task" if self.english else "没有找到相关操作")
            for browser in self.browsers:
                browser.setHtml(_paragraph("Try a shorter keyword or choose All tasks." if self.english else
                                           "试试更短的关键词，或把分类切回“全部操作”。"))
            return
        self.current = self.filtered[index]
        if self.current["id"] == "layout_ai" and self.owner is not None and not self.owner.state:
            self.open_button.setEnabled(False)
            self.open_button.setToolTip("Open a project first" if self.english else "打开项目后即可调整工作区")
        else:
            self.open_button.setToolTip("")
        self.selected_id = self.current["id"]
        self.chapter_label.setText(catalog_text(self.current, "title", self.language))
        for browser, section in zip(self.browsers, ("steps", "reference", "troubleshooting")):
            browser.setHtml(task_html(self.current, self.language, section))
            browser.verticalScrollBar().setValue(0)
        self.mark_read.setText(
            ("✓ Read" if self.english else "✓ 已读") if self.selected_id in self.read_ids else
            ("Mark as read" if self.english else "标为已读"))

    def _move(self, offset):
        self.list.setCurrentRow(max(0, min(len(self.filtered) - 1, self.list.currentRow() + offset)))

    def _toggle_read(self):
        if self.selected_id in self.read_ids:
            self.read_ids.remove(self.selected_id)
        else:
            self.read_ids.add(self.selected_id)
        self.settings.setValue("help/read_tasks", ",".join(sorted(self.read_ids)))
        self._filter()

    def _zoom(self, delta):
        self.font_size = max(10, min(17, self.font_size + delta))
        self.settings.setValue("help/font_size", self.font_size)
        self._apply_font()

    def _apply_font(self):
        for browser in self.browsers:
            browser.document().setDefaultFont(QFont("Microsoft YaHei", self.font_size))
        self.zoom_out.setEnabled(self.font_size > 10)
        self.zoom_in.setEnabled(self.font_size < 17)

    def _navigate(self):
        if self.owner is None:
            return
        self.accept()
        parent = self.parentWidget()
        if parent is not self.owner and isinstance(parent, QDialog):
            parent.accept()
        self.owner._navigate_from_tutorial(self.current)

    def _open_full_manual(self):
        # Import lazily to keep the standalone tutorial renderer independent.
        from .ui import _documentation_page
        page = _documentation_page(self.language, "task-guide.html")
        url = QUrl.fromLocalFile(str(page)) if Path(page).exists() else QUrl(
            "https://carbonlack.github.io/neuroflow-ai/" + ("en/" if self.english else "zh/"))
        if page.exists() and self.selected_id:
            url.setFragment("task-" + self.selected_id)
        QDesktopServices.openUrl(url)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "splitter"):
            vertical = self.width() < 760
            orientation = Qt.Vertical if vertical else Qt.Horizontal
            if self.splitter.orientation() != orientation:
                self.splitter.setOrientation(orientation)
                self.splitter.setSizes([150, 460] if vertical else [250, 750])
            self.list.setMaximumHeight(130 if vertical else 16777215)
