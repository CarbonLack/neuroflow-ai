"""Native, continuous, vector-first viewer for publication figures."""
from __future__ import annotations

import html
import json
import copy
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QInputDialog, QLabel, QPushButton, QScrollArea,
    QLayout, QSizePolicy, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)


class PublicationGallery(QWidget):
    """Show the complete manuscript story as one vertically scrollable document."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(205)
        self.tree.currentItemChanged.connect(self._display)
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(self.tree, 1)
        actions = QHBoxLayout()
        self.move_up = QPushButton("↑")
        self.move_down = QPushButton("↓")
        self.edit_caption = QPushButton("Edit caption")
        self.to_main = QPushButton("Choose for Main")
        self.to_extended = QPushButton("Send to Extended")
        self.move_up.clicked.connect(lambda: self._move_selected(-1))
        self.move_down.clicked.connect(lambda: self._move_selected(1))
        self.edit_caption.clicked.connect(self._edit_selected_caption)
        self.to_main.clicked.connect(lambda: self._assign_selected("main"))
        self.to_extended.clicked.connect(lambda: self._assign_selected("supplementary"))
        for button in (
            self.move_up, self.move_down, self.edit_caption,
            self.to_main, self.to_extended,
        ):
            actions.addWidget(button)
        sidebar_layout.addLayout(actions)
        splitter.addWidget(sidebar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.viewport().installEventFilter(self)
        self.gallery_content = QWidget()
        self.gallery_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.gallery_layout = QVBoxLayout(self.gallery_content)
        self.gallery_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.gallery_layout.setContentsMargins(18, 12, 18, 28)
        self.gallery_layout.setSpacing(26)
        self.heading = QLabel("Run the publication step to generate figures.")
        self.heading.setWordWrap(True)
        self.heading.setStyleSheet("font-size:18px;font-weight:700;")
        self.gallery_layout.addWidget(self.heading)
        # Compatibility handles for older tests/projects; new composites use
        # vector QSvgWidget cards instead of this raster label.
        self.image = QLabel()
        self.image.hide()
        self.caption = QLabel()
        self.caption.setWordWrap(True)
        self.caption.hide()
        self.gallery_layout.addStretch()
        self.scroll.setWidget(self.gallery_content)
        splitter.addWidget(self.scroll)
        splitter.setStretchFactor(1, 5)
        layout.addWidget(splitter)

        self._pixmap = QPixmap()
        self.exports: Path | None = None
        self.current_figure_name = ""
        self._groups: list[dict] = []
        self._cards: list[QWidget] = []
        self._card_media: list[tuple[QWidget, float]] = []

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
            "schema": "neuroephys.publication-storyboard.v3",
            "policy": "All source plots are retained; representative panels may be assigned to main or extended-data figures.",
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
            image = str(group["composite_svg"]).removeprefix("publication/")
            panel_text = "".join(
                f"<p><b>({p['panel']}) {html.escape(p['title'])}.</b> "
                f"{html.escape(p.get('caption_draft', ''))}</p>"
                for p in group["panels"])
            blocks.append(f"<section><h2>{html.escape(group['figure'])}. "
                          f"{html.escape(group['story_role'])}</h2>"
                          f"<img src=\"{html.escape(image, quote=True)}\">"
                          f"{panel_text}</section>")
        (publication / "index.html").write_text(
            "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
            "<title>Publication figures</title><style>body{font:14px Arial,sans-serif;"
            "max-width:1050px;margin:32px auto;padding:0 20px;color:#222}section{"
            "break-inside:avoid;margin:36px 0}img{display:block;max-width:100%;"
            "width:760px;height:auto;margin:16px auto}p{line-height:1.5}"
            "@media print{section{break-before:page}}</style>"
            "<h1>Publication figure draft</h1><p>All source plots are retained. "
            "Author and journal-specific scientific review is required.</p>"
            + "".join(blocks) + "</html>", encoding="utf-8")

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

    def _assign_selected(self, role: str) -> None:
        """Move a chosen evidence panel between main and Extended Data.

        A one-panel source figure is copied instead of emptied, so no result is
        lost merely because the author chose a representative main panel.
        """
        item = self.tree.currentItem()
        if not item or not item.parent() or not self.exports:
            return
        source_index = self.tree.indexOfTopLevelItem(item.parent())
        if source_index < 0:
            return
        source = self._groups[source_index]
        panel_index = item.parent().indexOfChild(item)
        selected_panel = source["panels"][panel_index]
        source_figure = str(selected_panel.get("figure_name", ""))
        # A Unit-level PSTH/raster is a four-panel scientific object. Choosing
        # one of its axes promotes/demotes the complete Unit response instead
        # of silently separating raster, PSTH, heat map and effect-size panel.
        if source_figure.startswith("raster_psth_"):
            source_indices = [
                index for index, row in enumerate(source["panels"])
                if row.get("figure_name") == source_figure
            ]
        else:
            source_indices = [panel_index]
        selected_panels = [
            copy.deepcopy(source["panels"][index]) for index in source_indices
        ]
        candidates = [
            group for group in self._groups
            if group.get("role", "main") == role and group is not source
        ]
        if role == "main":
            preferred = [group for group in candidates
                         if "Event-aligned" in group.get("story_role", "")]
        else:
            preferred = [group for group in candidates
                         if "Unit-level event" in group.get("story_role", "")]
        target = (preferred or candidates or [None])[0]
        if target is None:
            return
        if role == "main" and source_figure.startswith("raster_psth_unit_"):
            previous_representative = [
                row for row in target.get("panels", [])
                if str(row.get("figure_name", "")).startswith("raster_psth_")
            ]
            target["panels"] = [
                row for row in target.get("panels", [])
                if row not in previous_representative
            ]
            source_existing = {
                row["source_panel_svg"] for row in source.get("panels", [])
            }
            source.setdefault("panels", []).extend(
                copy.deepcopy(row) for row in previous_representative
                if row["source_panel_svg"] not in source_existing
            )
        existing = {row["source_panel_svg"] for row in target.get("panels", [])}
        target.setdefault("panels", []).extend(
            row for row in selected_panels if row["source_panel_svg"] not in existing
        )
        removed = len(source.get("panels", [])) > len(source_indices)
        if removed:
            for index in sorted(source_indices, reverse=True):
                source["panels"].pop(index)
        for group in (source, target):
            for index, row in enumerate(group.get("panels", [])):
                row["panel"] = chr(ord("a") + index)
        from .publication_compositor import rebuild_publication_figure
        if removed:
            rebuild_publication_figure(self.exports, source)
        self._persist(target)
        target_label = target["figure"]
        self.load(self.exports)
        for index, group in enumerate(self._groups):
            if group["figure"] == target_label:
                self.tree.setCurrentItem(self.tree.topLevelItem(index))
                break

    def _clear_cards(self) -> None:
        while self.gallery_layout.count() > 1:
            item = self.gallery_layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards = []
        self._card_media = []

    def load(self, exports: Path | None) -> bool:
        self.exports = exports
        self.tree.clear()
        self._pixmap = QPixmap()
        self.current_figure_name = ""
        self._clear_cards()
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
        self.heading.setText(
            "Publication story · main figures followed by complete extended-data evidence"
        )
        for group in groups:
            group_item = QTreeWidgetItem([f"{group['figure']} · {group['story_role']}"])
            group_item.setData(0, Qt.UserRole, group)
            self.tree.addTopLevelItem(group_item)
            for panel in group.get("panels", []):
                item = QTreeWidgetItem([f"({panel['panel']}) {panel['title']}"])
                item.setData(0, Qt.UserRole, panel)
                group_item.addChild(item)
            self._add_group_card(group)
        self.gallery_layout.addStretch()
        self._groups = groups
        first = self.tree.topLevelItem(0)
        if first:
            self.tree.setCurrentItem(first)
        return bool(groups)

    def _add_group_card(self, group: dict) -> None:
        card = QFrame()
        card.setObjectName("publicationFigureCard")
        card.setStyleSheet(
            "QFrame#publicationFigureCard{background:#ffffff;border:1px solid #cfd6dc;"
            "border-radius:7px;} QLabel{color:#20272d;}"
        )
        column = QVBoxLayout(card)
        column.setContentsMargins(20, 16, 20, 18)
        role = "MAIN FIGURE" if group.get("role", "main") == "main" else "EXTENDED DATA"
        heading = QLabel(f"{role} · {group['figure']}\n{group['story_role']}")
        heading.setStyleSheet("font-size:17px;font-weight:700;")
        heading.setWordWrap(True)
        column.addWidget(heading)
        media: QWidget
        aspect = 0.7
        composite = group.get("composite_svg")
        if composite and (self.exports / composite).is_file():
            media = QSvgWidget(str(self.exports / composite))
            renderer_size = media.renderer().defaultSize()
            if renderer_size.width() > 0:
                aspect = renderer_size.height() / renderer_size.width()
        else:
            legacy_panel = (group.get("panels") or [{}])[0]
            name = Path(str(legacy_panel.get("source_svg", ""))).stem
            png = self.exports / "figures" / f"{name}.png"
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            if png.is_file():
                pixmap = QPixmap(str(png))
                label.setPixmap(pixmap)
                label._source_pixmap = pixmap
                if pixmap.width() > 0:
                    aspect = pixmap.height() / pixmap.width()
            media = label
        media.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        column.addWidget(media)
        details = []
        for panel in group.get("panels", []):
            data_path = panel.get("plotted_data") or (
                f"figure_data/{Path(str(panel.get('source_svg', ''))).stem}.json")
            details.append(
                f"<b>({panel['panel']}) {html.escape(panel['title'])}.</b> "
                f"{html.escape(panel.get('caption_draft', ''))}<br>"
                f"<span style='color:#60717b'>Plotted data: {html.escape(data_path)} "
                f"· source axis {panel.get('source_axis', '?')}</span>"
            )
        caption = QLabel("<br><br>".join(details))
        caption.setWordWrap(True)
        caption.setTextFormat(Qt.RichText)
        column.addWidget(caption)
        trace = QLabel(
            "Traceability: exports/provenance.json · exports/figure_data/*.json/.npz "
            "· original per-panel SVG. Captions remain author-editable."
        )
        trace.setWordWrap(True)
        trace.setStyleSheet("color:#60717b;font-size:11px;")
        column.addWidget(trace)
        self.gallery_layout.addWidget(card)
        self._cards.append(card)
        self._card_media.append((media, aspect))
        self._resize_media(media, aspect)

    def _display(self, item, _previous) -> None:
        if item is None or not self.exports:
            return
        payload = item.data(0, Qt.UserRole)
        if not isinstance(payload, dict):
            return
        parent = item.parent()
        group_index = (
            self.tree.indexOfTopLevelItem(item)
            if parent is None else self.tree.indexOfTopLevelItem(parent)
        )
        if group_index < 0 or group_index >= len(self._groups):
            return
        group = self._groups[group_index]
        self.current_figure_name = group.get("figure", "")
        if not group.get("composite_svg"):
            legacy_panel = payload if "source_svg" in payload else (group.get("panels") or [{}])[0]
            self.current_figure_name = Path(str(legacy_panel.get("source_svg", ""))).stem
        details = []
        for panel in group.get("panels", []):
            data_path = panel.get("plotted_data") or (
                f"figure_data/{Path(str(panel.get('source_svg', ''))).stem}.json")
            details.append(
                f"({panel['panel']}) {panel['title']}. {panel.get('caption_draft', '')}\n"
                f"Data: {data_path} · Source axis: {panel.get('source_axis', '?')}"
            )
        self.caption.setText("\n\n".join(details))
        if group_index < len(self._cards):
            self.scroll.ensureWidgetVisible(self._cards[group_index], 0, 18)

    def resizeEvent(self, event):  # noqa: N802 - Qt API
        super().resizeEvent(event)
        QTimer.singleShot(0, self._resize_all_media)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        if watched is self.scroll.viewport() and event.type() == QEvent.Resize:
            QTimer.singleShot(0, self._resize_all_media)
        return super().eventFilter(watched, event)

    def _resize_media(self, media: QWidget, aspect: float) -> None:
        width = max(320, self.scroll.viewport().width() - 95)
        media.setFixedHeight(max(220, min(1350, int(width * aspect))))
        pixmap = getattr(media, "_source_pixmap", None)
        if pixmap is not None and not pixmap.isNull():
            media.setPixmap(pixmap.scaled(width, media.height(), Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation))

    def _resize_all_media(self) -> None:
        for media, aspect in self._card_media:
            self._resize_media(media, aspect)

    def _resize_image(self) -> None:
        self._resize_all_media()
