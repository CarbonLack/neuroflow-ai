from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from neuroflow.ai_conversations import (
    LEGACY_THREAD_ID, create_thread, ensure_threads, group_label, matching_threads,
    load_general_conversations, record_in_thread, rename_thread,
    save_general_conversations, set_thread_group, thread_records,
)
from neuroflow.ai_ui import ChatComposer
from neuroflow.ai_project_bridge import ProjectQueries
from neuroflow.models import ProjectState
from neuroflow.project import restore_ai_conversation, save_ai_conversation


def test_legacy_history_is_preserved_and_searchable():
    metadata = {"ai_history": [{"question": "旧的质控问题", "answer": "先查坏通道"}]}
    threads = ensure_threads(metadata)
    assert threads[0]["id"] == LEGACY_THREAD_ID
    assert len(thread_records(metadata, LEGACY_THREAD_ID)) == 1
    new_id = create_thread(metadata)
    record_in_thread(metadata, {"question": "Neuropixels 图怎么看", "answer": "看时间轴"}, new_id)
    assert metadata["ai_threads"][-1]["title"] == "Neuropixels 图怎么看"
    assert [row["id"] for row in matching_threads(metadata, "时间轴")] == [new_id]
    assert rename_thread(metadata, new_id, "解码讨论")
    assert metadata["ai_threads"][-1]["title"] == "解码讨论"
    assert set_thread_group(metadata, new_id, "methods")
    assert metadata["ai_threads"][-1]["group"] == "methods"
    assert group_label("methods") == "方法问答"
    assert [row["id"] for row in matching_threads(metadata, "方法问答")] == [new_id]
    assert threads[0]["group"] == "earlier"
    assert len(metadata["ai_history"]) == 2


def test_composer_enter_sends_and_shift_enter_adds_line():
    app = QApplication.instance() or QApplication([])
    composer = ChatComposer()
    sent = []
    composer.submitted.connect(lambda: sent.append(composer.toPlainText()))
    composer.setPlainText("First question")
    composer.moveCursor(QTextCursor.End)
    QTest.keyClick(composer, Qt.Key_Return, Qt.ShiftModifier)
    assert composer.toPlainText().endswith("\n")
    QTest.keyClick(composer, Qt.Key_Return)
    assert sent == [composer.toPlainText()]
    composer.close()
    app.processEvents()


def test_app_guidance_is_from_versioned_tutorial():
    queries = ProjectQueries(None, "sorting", "assistant")
    result = queries.guidance("sorting", "en_US")
    guides = result["result"]["guides"]
    assert guides
    assert any("sorting" in guide["title"].lower() for guide in guides)
    assert all(guide["steps"] for guide in guides)


def test_thread_archive_roundtrip_and_old_archive_upgrade(tmp_path):
    state = ProjectState(root=tmp_path)
    thread_id = create_thread(state.metadata)
    record_in_thread(state.metadata, {"question": "How to sort?", "answer": "Inspect QC."}, thread_id)
    save_ai_conversation(state)
    reopened = ProjectState(root=tmp_path)
    restore_ai_conversation(reopened)
    assert reopened.metadata["ai_threads"][0]["title"] == "How to sort"
    assert reopened.metadata["ai_threads"][0]["group"] == "project"
    assert thread_records(reopened.metadata, thread_id)[0]["answer"] == "Inspect QC."

    import json
    archive = tmp_path / "ai" / "conversation.json"
    archive.write_text(json.dumps([{"question": "Legacy", "answer": "Still here"}]), encoding="utf-8")
    old = ProjectState(root=tmp_path)
    restore_ai_conversation(old)
    assert ensure_threads(old.metadata)[0]["id"] == LEGACY_THREAD_ID
    assert old.metadata["ai_history"][0]["answer"] == "Still here"


def test_projectless_general_chat_survives_app_restart(tmp_path):
    path = tmp_path / "ai" / "general_conversation.json"
    metadata = load_general_conversations(path)
    thread_id = create_thread(metadata, group="general")
    record_in_thread(metadata, {"question": "What is an ISI?", "answer": "An inter-spike interval."}, thread_id)
    metadata["ai_active_thread_id"] = thread_id
    save_general_conversations(path, metadata)
    restored = load_general_conversations(path)
    assert restored["ai_active_thread_id"] == thread_id
    assert thread_records(restored, thread_id)[0]["answer"] == "An inter-spike interval."
    assert matching_threads(restored, "ISI")[0]["title"] == "What is an ISI"
