"""Native, project-local viewer for exported publication figures."""
from __future__ import annotations

import json
import html
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QPushButton, QScrollArea, QSplitter,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)


class PublicationGallery(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(180)
        self.tree.currentItemChanged.connect(self._display)
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(self.tree, 1)
        actions = QHBoxLayout()
        self.move_up = QPushButton("↑")
        self.move_down = QPushButton("↓")
        self.edit_caption = QPushButton("Edit caption")
        self.move_up.clicked.connect(lambda: self._move_selected(-1))
        self.move_down.clicked.connect(lambda: self._move_selected(1))
        self.edit_caption.clicked.connect(self._edit_selected_caption)
        for button in (self.move_up, self.move_down, self.edit_caption):
            actions.addWidget(button)
        sidebar_layout.addLayout(actions)
        splitter.addWidget(sidebar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        column = QVBoxLayout(content)
        self.heading = QLabel()
        self.heading.setWordWrap(True)
        column.addWidget(self.heading)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignCenter)
        column.addWidget(self.image)
        self.caption = QLabel()
        self.caption.setWordWrap(True)
        column.addWidget(self.caption)
        column.addStretch()
        self.scroll.setWidget(content)
        self.scroll.viewport().installEventFilter(self)
        splitter.addWidget(self.scroll)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter)
        self._pixmap = QPixmap()
        self.exports: Path | None = None
        self.current_figure_name = ""
        self._groups: list[dict] = []

    def _persist(self, changed: dict) -> None:
        if not self.exports:
            return
        from .publication_compositor import rebuild_publication_figure
        publication = self.exports / "publication"
        edits_file = publication / "author_edits.json"
        edits = (json.loads(edits_file.read_text(encoding="utf-8"))
                 if edits_file.is_file() else {})
        for group in self._groups:
            edits[group["figure"]] = {
                "panel_order": [p["source_panel_svg"] for p in group["panels"]],
                "captions": {p["source_panel_svg"]: p.get("caption_draft", "")
                             for p in group["panels"]},
            }
        rebuild_publication_figure(self.exports, changed)
        edits_file.write_text(json.dumps(edits, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        (publication / "storyboard.json").write_text(json.dumps({
            "schema": "neuroephys.publication-storyboard.v2",
            "policy": "All source plots included regardless of significance.",
            "figures": self._groups,
            "complete_artifact_inventory": "artifact_inventory.json",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        legends = ["# Figure legends — author review required", ""]
        for group in self._groups:
            legends += [f"## {group['figure']}. {group['story_role']}", ""]
            legends += [f"**({p['panel']}) {p['title']}.** {p.get('caption_draft', '')}"
                        for p in group["panels"]]
            legends += [""]
        (publication / "figure_legends.md").write_text("\n".join(legends),
                                                        encoding="utf-8")
        blocks = []
        for group in self._groups:
            image = str(group['composite_svg']).removeprefix('publication/')
            panel_text = ''.join(
                f"<p><b>({p['panel']}) {html.escape(p['title'])}.</b> "
                f"{html.escape(p.get('caption_draft', ''))}</p>"
                for p in group['panels'])
            blocks.append(f"<section><h2>{html.escape(group['figure'])}. "
                          f"{html.escape(group['story_role'])}</h2>"
                          f"<img src=\"{html.escape(image, quote=True)}\">"
                          f"{panel_text}</section>")
        (publication / "index.html").write_text(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<title>Publication figures</title><style>body{font:14px Arial,sans-serif;'
            'max-width:1050px;margin:32px auto;padding:0 20px;color:#222}section{'
            'break-inside:avoid;margin:36px 0}img{display:block;max-width:100%;'
            'width:760px;height:auto;margin:16px auto}p{line-height:1.5}'
            '@media print{section{break-before:page}}</style>'
            '<h1>Publication figure draft</h1><p>All source plots are retained. '
            'Author and journal-specific scientific review is required.</p>'
            + ''.join(blocks) + '</html>', encoding='utf-8')

    def _move_selected(self, direction: int) -> None:
        item = self.tree.currentItem()
        if not item or not item.parent():
            return
        group_index = self.tree.indexOfTopLevelItem(item.parent())
        if group_index < 0:
            return
        group = self._groups[group_index]
        index = item.parent().indexOfChild(item)
        other = index + direction
        if other < 0 or other >= len(group["panels"]):
            return
        group["panels"][index], group["panels"][other] = (
            group["panels"][other], group["panels"][index])
        for n, panel in enumerate(group["panels"]):
            panel["panel"] = chr(ord("a") + n)
        figure_label = group["figure"]
        self._persist(group)
        self.load(self.exports)
        for figure_index, current in enumerate(self._groups):
            if current["figure"] == figure_label:
                self.tree.setCurrentItem(self.tree.topLevelItem(figure_index).child(other))
                break

    def _edit_selected_caption(self) -> None:
        item = self.tree.currentItem()
        if not item or not item.parent():
            return
        group_index = self.tree.indexOfTopLevelItem(item.parent())
        if group_index < 0:
            return
        group = self._groups[group_index]
        panel = group["panels"][item.parent().indexOfChild(item)]
        value, accepted = QInputDialog.getMultiLineText(
            self, "Figure caption", "English caption draft:",
            panel.get("caption_draft", ""))
        if accepted:
            panel["caption_draft"] = value
            self._persist(group)
            panel_index = item.parent().indexOfChild(item)
            self.load(self.exports)
            self.tree.setCurrentItem(
                self.tree.topLevelItem(group_index).child(panel_index))

    def load(self, exports: Path | None) -> bool:
        self.exports = exports
        self.tree.clear()
        self._pixmap = QPixmap()
        self.current_figure_name = ""
        self.image.clear()
        self.heading.setText("Run the publication step to generate figures.")
        self.caption.clear()
        self._groups = []
        if exports is None:
            return False
        storyboard = exports / "publication" / "storyboard.json"
        if not storyboard.is_file():
            return False
        try:
            groups = json.loads(storyboard.read_text(encoding="utf-8"))["figures"]
        except (OSError, ValueError, KeyError, TypeError):
            self.heading.setText("The publication index cannot be read; rerun the export step.")
            return False
        for group in groups:
            group_item = QTreeWidgetItem([f"{group['figure']} · {group['story_role']}"])
            group_item.setData(0, Qt.UserRole, group)
            self.tree.addTopLevelItem(group_item)
            for panel in group.get("panels", []):
                item = QTreeWidgetItem([f"({panel['panel']}) {panel['title']}"])
                item.setData(0, Qt.UserRole, panel)
                group_item.addChild(item)
            group_item.setExpanded(False)
        first = self.tree.topLevelItem(0)
        self._groups = groups
        if first:
            self.tree.setCurrentItem(first)
        return bool(groups)

    def _display(self, item, _previous) -> None:
        if item is None or not self.exports:
            return
        payload = item.data(0, Qt.UserRole)
        if not isinstance(payload, dict):
            return
        group = payload if "panels" in payload else item.parent().data(0, Qt.UserRole)
        if not isinstance(group, dict):
            return
        composite = group.get("composite_png")
        if composite:
            self.current_figure_name = group["figure"]
            png = (self.exports / composite).resolve()
            allowed = (self.exports / "publication" / "figures").resolve()
            valid = png.parent == allowed
        else:
            legacy_panel = (payload if "source_svg" in payload else
                            (group.get("panels") or [{}])[0])
            name = Path(str(legacy_panel.get("source_svg", ""))).stem
            self.current_figure_name = name
            png = (self.exports / "figures" / f"{name}.png").resolve()
            valid = png.parent == (self.exports / "figures").resolve()
        if not valid or not png.is_file():
            self.heading.setText("Figure file is missing; rerun the export step.")
            self.image.clear()
            return
        self._pixmap = QPixmap(str(png))
        self.heading.setText(f"{group['figure']} · {group['story_role']}")
        details = []
        for panel in group.get("panels", []):
            data_path = panel.get("plotted_data") or (
                f"figure_data/{Path(str(panel.get('source_svg', ''))).stem}.json")
            details.append(f"({panel['panel']}) {panel['title']}. "
                           f"{panel.get('caption_draft', '')}\n"
                           f"Data: {data_path} "
                           f"· Source axis: {panel.get('source_axis', '?')}")
        details.append("Original recording and parameters: exports/provenance.json; "
                       "exports/figure_data/*.json. Author interpretation is editable "
                       "in the figure legend draft.")
        self.caption.setText("\n\n".join(details))
        self._resize_image()

    def resizeEvent(self, event):  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._resize_image()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        if watched is self.scroll.viewport() and event.type() == QEvent.Resize:
            QTimer.singleShot(0, self._resize_image)
        return super().eventFilter(watched, event)

    def _resize_image(self) -> None:
        if not self._pixmap.isNull():
            width = max(200, self.scroll.viewport().width() - 36)
            self.image.setPixmap(self._pixmap.scaledToWidth(width, Qt.SmoothTransformation))
