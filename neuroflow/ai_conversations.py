"""Project-owned, searchable AI conversation threads.

Older projects stored one flat ``ai_history`` list.  This module preserves those
records and gives them a single legacy thread; no answer is discarded or rewritten.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

LEGACY_THREAD_ID = "legacy-conversation"
THREAD_GROUPS = ("project", "figures", "methods", "general", "earlier")


def group_label(group: str, language: str = "zh_CN") -> str:
    labels = {
        "project": ("项目分析", "Project"),
        "figures": ("图表解读", "Figures"),
        "methods": ("方法问答", "Methods"),
        "general": ("通用问题", "General"),
        "earlier": ("早期对话", "Earlier"),
    }
    translated = labels.get(group, labels["project"])
    return translated[1] if language == "en_US" else translated[0]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def title_from_question(question: str, *, limit: int = 42) -> str:
    title = re.sub(r"\s+", " ", question).strip().strip("？?。.!！")
    return title[:limit].rstrip() + ("…" if len(title) > limit else "") or "New conversation"


def ensure_threads(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    records = metadata.setdefault("ai_history", [])
    threads = metadata.setdefault("ai_threads", [])
    if not isinstance(records, list) or not isinstance(threads, list):
        raise ValueError("AI conversation archive has an invalid structure")
    if records and any(not row.get("thread_id") for row in records if isinstance(row, dict)):
        for row in records:
            if isinstance(row, dict):
                row.setdefault("thread_id", LEGACY_THREAD_ID)
        if not any(row.get("id") == LEGACY_THREAD_ID for row in threads):
            threads.insert(0, {"id": LEGACY_THREAD_ID, "title": "Earlier conversation",
                               "created_at": str(records[0].get("created_at", "")) or _now(),
                               "group": "earlier",
                               "automatic_title": False})
    known = {str(row.get("id", "")) for row in threads if isinstance(row, dict)}
    for row in records:
        if isinstance(row, dict) and row.get("thread_id") and row["thread_id"] not in known:
            thread_id = str(row["thread_id"])
            threads.append({"id": thread_id,
                            "title": title_from_question(str(row.get("question", ""))),
                            "created_at": str(row.get("created_at", "")) or _now(),
                            "group": "earlier" if thread_id == LEGACY_THREAD_ID else "project",
                            "automatic_title": False})
            known.add(thread_id)
    if not threads:
        create_thread(metadata)
    for row in threads:
        if isinstance(row, dict) and row.get("group") not in THREAD_GROUPS:
            row["group"] = "earlier" if row.get("id") == LEGACY_THREAD_ID else "project"
    return threads


def create_thread(metadata: dict[str, Any], title: str = "", group: str = "project") -> str:
    if group not in THREAD_GROUPS:
        raise ValueError("Unknown AI conversation group")
    threads = metadata.setdefault("ai_threads", [])
    thread_id = "chat-" + uuid.uuid4().hex
    threads.append({"id": thread_id, "title": title.strip()[:80] or "New conversation",
                    "created_at": _now(), "group": group,
                    "automatic_title": not bool(title.strip())})
    return thread_id


def set_thread_group(metadata: dict[str, Any], thread_id: str, group: str) -> bool:
    if group not in THREAD_GROUPS:
        return False
    for thread in ensure_threads(metadata):
        if thread.get("id") == thread_id:
            thread["group"] = group
            return True
    return False


def rename_thread(metadata: dict[str, Any], thread_id: str, title: str) -> bool:
    clean = re.sub(r"\s+", " ", title).strip()[:80]
    if not clean:
        return False
    for thread in ensure_threads(metadata):
        if thread.get("id") == thread_id:
            thread["title"] = clean
            thread["automatic_title"] = False
            return True
    return False


def record_in_thread(metadata: dict[str, Any], record: dict[str, Any], thread_id: str) -> None:
    threads = ensure_threads(metadata)
    thread = next((row for row in threads if row.get("id") == thread_id), None)
    if thread is None:
        raise ValueError("Unknown AI conversation thread")
    record["thread_id"] = thread_id
    metadata.setdefault("ai_history", []).append(record)
    if thread.get("automatic_title"):
        thread["title"] = title_from_question(str(record.get("question", "")))
        thread["automatic_title"] = False


def thread_records(metadata: dict[str, Any], thread_id: str) -> list[dict[str, Any]]:
    return [row for row in metadata.get("ai_history", [])
            if isinstance(row, dict) and row.get("thread_id", LEGACY_THREAD_ID) == thread_id]


def matching_threads(metadata: dict[str, Any], query: str = "") -> list[dict[str, Any]]:
    words = re.findall(r"\w+", query.casefold())
    matches = []
    for thread in ensure_threads(metadata):
        rows = thread_records(metadata, str(thread["id"]))
        haystack = " ".join([str(thread.get("title", "")),
                             group_label(str(thread.get("group", "project"))),
                             group_label(str(thread.get("group", "project")), "en_US")] + [
            str(row.get("question", "")) + " " + str(row.get("answer", ""))
            for row in rows
        ]).casefold()
        if all(word in haystack for word in words):
            matches.append(thread)
    newest_first = list(reversed(matches))
    return sorted(newest_first, key=lambda row: THREAD_GROUPS.index(str(row.get("group", "project"))))
