"""Project-scoped, bounded queries shared by the GUI and the Harness MCP bridge."""
from __future__ import annotations

import copy
import dataclasses
import hmac
import json
import math
import re
import secrets
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .ai import build_project_summary, redact_sensitive_text
from .ai_tools import AIMode, TOOL_REGISTRY, validate_tool_call
from .models import ProjectState
from .tutorial_catalog import TUTORIAL_CATALOG


def safe_value(value: Any, depth: int = 0) -> Any:
    """Convert only the requested bounded result, never serialize entire arrays."""
    if isinstance(value, Path):
        return "<local-path>"
    if isinstance(value, str):
        return redact_sensitive_text(value)[:12000]
    if isinstance(value, np.generic):
        return safe_value(value.item(), depth)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if depth > 6:
        return {"kind": type(value).__name__, "detail": "Query this nested path separately"}
    if isinstance(value, np.ndarray):
        if value.size > 100:
            return {"kind": "array", "shape": list(value.shape), "dtype": str(value.dtype), "query_required": True}
        return safe_value(value.tolist(), depth + 1)
    if isinstance(value, dict):
        return {str(k): safe_value(v, depth + 1) for k, v in list(value.items())[:100]
                if not any(t in str(k).lower() for t in ("path", "secret", "api_key", "token", "credential"))}
    if isinstance(value, (list, tuple)):
        return [safe_value(v, depth + 1) for v in value[:100]]
    return {"kind": type(value).__name__}


class ProjectQueries:
    """One immutable GUI-thread snapshot per request; no Qt access from MCP."""

    def __init__(self, state: ProjectState | None, stage: str, mode: str):
        self.snapshot_id = secrets.token_hex(8)
        self.captured_at = datetime.now(timezone.utc).isoformat()
        self.mode = mode
        self.stage = stage
        self._exports = state.root / "exports" if state is not None else None
        self.summary = build_project_summary(state, stage, include_recent_log=True)
        if self._exports is not None and stage == "export":
            storyboard = self._exports / "publication" / "storyboard.json"
            if storyboard.is_file():
                try:
                    groups = json.loads(storyboard.read_text(encoding="utf-8")).get("figures", [])
                    self.summary["publication_figures"] = [
                        {"figure": item.get("figure"), "story_role": item.get("story_role"),
                         "panel_count": len(item.get("panels", []))}
                        for item in groups[:40]]
                except (OSError, ValueError, TypeError):
                    pass
        self.state = None
        self.sections: dict[str, Any] = {}
        if state is not None:
            self.state = copy.copy(state)
            excluded = {"root", "source_path", "recording_path", "ground_truth"}
            for f in dataclasses.fields(state):
                if f.name not in excluded:
                    value = copy.deepcopy(getattr(state, f.name))
                    setattr(self.state, f.name, value)
                    if isinstance(value, (dict, list, np.ndarray)):
                        self.sections[f.name] = value
        self.audit: list[dict[str, Any]] = []
        self.proposals: list[dict[str, Any]] = []
        self.allowed_sections: set[str] | None = None
        self._lock = threading.Lock()

    def _result(self, tool: str, arguments: dict, data: Any) -> dict:
        with self._lock:
            evidence_id = f"Q{len(self.audit) + 1}"
            record = {"evidence_id": evidence_id, "tool": tool,
                      "arguments": safe_value(arguments), "snapshot_id": self.snapshot_id,
                      "captured_at": self.captured_at, "result": safe_value(data)}
            self.audit.append(record)
        return record

    def context(self) -> dict:
        return self._result("get_current_context", {}, self.summary)

    def catalog(self) -> dict:
        sections = {key: {"kind": type(value).__name__, "count": len(value)}
                    for key, value in self.sections.items()
                    if self.allowed_sections is None or key in self.allowed_sections}
        actions = {name: {"description": spec.description, "parameters": spec.input_schema,
                          "confirmation_required": spec.confirmation_required}
                   for name, spec in TOOL_REGISTRY.items()}
        return self._result("list_project_data", {}, {"sections": sections,
            "actions": actions, "raw_voltage": "Not exposed through this interface",
            "ground_truth": "Not included in ordinary analysis queries",
            "app_guidance": "Use search_app_guidance for built-in operation steps and scientific checks",
            "publication_figure_data": "Use query_figure_data for saved plotted arrays and provenance; export must be run first"})

    def figure_data(self, name: str = "", array: str = "", offset: int = 0,
                    limit: int = 100) -> dict:
        """Read only the exported figure-data bundle, never arbitrary paths or raw voltage."""
        if self._exports is None:
            return self._result("query_figure_data", {"name": name}, {"available": False})
        folder = self._exports / "figure_data"
        if not name:
            storyboard = self._exports / "publication" / "storyboard.json"
            composite_names = []
            if storyboard.is_file():
                try:
                    composite_names = [item.get("figure") for item in
                        json.loads(storyboard.read_text(encoding="utf-8")).get("figures", [])]
                except (OSError, ValueError, TypeError):
                    pass
            return self._result("query_figure_data", {}, {
                "figures": sorted(path.stem for path in folder.glob("*.json"))[:100],
                "composite_figures": composite_names[:40]})
        if re.fullmatch(r"(?:Figure|Extended Data Figure) \d{1,3}", name):
            if array:
                raise ValueError("Choose one source chart name from the composite panel list before querying numeric arrays.")
            storyboard = self._exports / "publication" / "storyboard.json"
            if not storyboard.is_file():
                raise ValueError("Publication figures have not been exported.")
            groups = json.loads(storyboard.read_text(encoding="utf-8")).get("figures", [])
            match = next((item for item in groups if item.get("figure") == name), None)
            if match is None:
                raise ValueError("Composite figure not found in this project.")
            return self._result("query_figure_data", {"name": name}, {
                "figure": name, "story_role": match.get("story_role"),
                "panels": [{"panel": item.get("panel"),
                            "source_chart": item.get("figure_name"),
                            "source_axis": item.get("source_axis"),
                            "array_axis_index": item.get("array_axis_index"),
                            "title": item.get("title"),
                            "caption_draft": item.get("caption_draft"),
                            "plotted_data": item.get("plotted_data")}
                           for item in match.get("panels", [])],
                "note": "Call query_figure_data again with source_chart to inspect arrays and provenance."})
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", name):
            raise ValueError("Invalid figure identifier.")
        manifest_path = folder / f"{name}.json"
        if not manifest_path.is_file():
            raise ValueError("Figure data are not exported; run publication export first.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("raw_recording", None)
        if not array:
            return self._result("query_figure_data", {"name": name}, manifest)
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", array):
            raise ValueError("Invalid array identifier.")
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("Use nonnegative offset and limit 1–100.")
        with np.load(folder / f"{name}.npz", allow_pickle=False) as archive:
            if array not in archive:
                raise ValueError("Array not found in this figure.")
            values = archive[array].reshape(-1)
            page = values[offset:offset + limit]
            result = {"figure": name, "array": array, "shape": list(archive[array].shape),
                      "offset": offset, "total": len(values), "values": page.tolist(),
                      "next_offset": offset + limit if offset + limit < len(values) else None}
        return self._result("query_figure_data", {"name": name, "array": array,
            "offset": offset, "limit": limit}, result)

    def guidance(self, query: str, language: str = "zh_CN", limit: int = 3) -> dict:
        """Search the versioned in-app tutorial; no network or project data read."""
        english = language == "en_US"
        needle = query.casefold().strip()
        terms = re.findall(r"[a-z0-9_-]+|[\u4e00-\u9fff]", needle)
        ranked = []
        for guide in TUTORIAL_CATALOG:
            haystack = " ".join(str(guide.get(key, "")) for key in
                ("id", "title", "title_en", "summary", "summary_en", "page_key", "category", "category_en")).casefold()
            score = sum(1 for term in terms if term in haystack)
            if needle and needle in haystack:
                score += 10
            if guide.get("page_key") == self.stage:
                score += 0.25
            if score > 0 or not needle:
                ranked.append((score, guide))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = [guide for _, guide in ranked[:max(1, min(limit, 5))]]
        rows = []
        for guide in selected:
            rows.append({
                "id": guide["id"],
                "title": guide["title_en" if english else "title"],
                "summary": guide["summary_en" if english else "summary"],
                "prerequisites": guide["prerequisites_en" if english else "prerequisites"],
                "steps": [
                    {"title": step["title_en" if english else "title"],
                     "instruction": step["body_en" if english else "body"]}
                    for step in guide["steps"]
                ],
                "check": guide["check_en" if english else "check"],
                "output": guide["output_en" if english else "output"],
                "reference": guide.get("reference", ""),
            })
        return self._result("search_app_guidance", {"query": query, "language": language},
                            {"guides": rows, "source": "versioned NeuroEphys AI tutorial catalog"})

    def query(self, section: str, path: list[str] | None = None, offset: int = 0,
              limit: int = 20, filters: dict[str, Any] | None = None) -> dict:
        if section not in self.sections or (self.allowed_sections is not None and section not in self.allowed_sections):
            raise ValueError("Section is unavailable or not selected for this conversation.")
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Use a nonnegative offset and a limit between 1 and 100.")
        value = self.sections[section]
        for part in path or []:
            if any(t in str(part).lower() for t in ("path", "secret", "api_key", "credential", "token")):
                raise ValueError("This metadata field is not exposed.")
            if isinstance(value, dict):
                key = part if part in value else int(part) if part.lstrip("-").isdigit() else part
                value = value[key]
            elif isinstance(value, (list, tuple, np.ndarray)):
                value = value[int(part)]
            else:
                raise ValueError("The requested path is not a container.")
        if filters:
            if not isinstance(value, list):
                raise ValueError("Row filters require a list of records.")
            value = [row for row in value if isinstance(row, dict) and
                     all(str(row.get(k)) == str(v) for k, v in filters.items())]
        if isinstance(value, dict):
            keys = list(value)
            rows = {str(k): value[k] for k in keys[offset:offset + limit]}
            total = len(keys)
        elif isinstance(value, (list, tuple, np.ndarray)):
            total = len(value)
            rows = value[offset:offset + limit]
        else:
            total, rows = 1, value
        return self._result("query_project_data", {"section": section, "path": path or [],
            "offset": offset, "limit": limit, "filters": filters or {}},
            {"total": total, "offset": offset, "next_offset": offset + limit if offset + limit < total else None,
             "data": rows, "note": "Stored values; consult acquisition/analysis metadata for units."})

    def history(self, query: str = "", limit: int = 10) -> dict:
        if self.allowed_sections is not None and "metadata" not in self.allowed_sections:
            raise ValueError("Project history is not selected for this conversation.")
        records = self.sections.get("metadata", {}).get("ai_history", [])
        # Natural-language tool queries rarely equal one contiguous substring.
        # Rank explicit keyword matches; do not invent semantic matches.
        terms = set(re.findall(r"[\w-]+", query.casefold()))
        ranked = []
        for index, record in enumerate(records):
            body = (str(record.get("question", "")) + " " + str(record.get("answer", ""))).casefold()
            score = sum(term in body for term in terms)
            if not terms or score:
                ranked.append((score, index, record))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        found = [item[2] for item in ranked[:max(1, min(limit, 20))]]
        return self._result("search_project_conversation", {"query": query, "matching": "ranked_keyword"}, found)

    def propose(self, name: str, arguments: dict[str, Any], reason: str = "") -> dict:
        validation = validate_tool_call(name, arguments, self.state, self.mode)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))
        proposal = {"name": name, "arguments": arguments, "reason": reason,
                    "id": secrets.token_hex(8), "snapshot_id": self.snapshot_id}
        with self._lock:
            self.proposals.append(proposal)
        return self._result("propose_analysis_action", {"name": name, "arguments": arguments},
            {"status": "awaiting_user_confirmation", "executed": False, "proposal_id": proposal["id"]})


class ProjectMCPBridge:
    """Short-lived loopback server. Token never enters model messages or project logs."""

    def __init__(self, queries: ProjectQueries):
        self.queries = queries
        self.token = secrets.token_urlsafe(32)
        self.server = None
        self.thread = None
        self.socket = None

    def __enter__(self):
        from mcp.server.fastmcp import FastMCP
        import uvicorn

        mcp = FastMCP("NeuroEphys", json_response=True, stateless_http=True)
        queries = self.queries

        @mcp.tool()
        def get_current_context() -> dict:
            """Read the current project, visible chart labels, workflow and results snapshot."""
            return queries.context()

        @mcp.tool()
        def list_project_data() -> dict:
            """List queryable data sections and registered analysis actions with parameter schemas."""
            return queries.catalog()

        @mcp.tool()
        def query_project_data(section: str, path: list[str] | None = None,
                               offset: int = 0, limit: int = 20,
                               filters: dict[str, Any] | None = None) -> dict:
            """Read a page of actual events, trials, unit metrics, spikes, logs or nested results.
            Use list_project_data first. Path selects nested keys; filters match record fields.
            Query deeper paths when arrays or objects are summarized. No file paths or raw voltage.
            """
            return queries.query(section, path, offset, limit, filters)

        @mcp.tool()
        def query_figure_data(name: str = "", array: str = "", offset: int = 0,
                              limit: int = 100) -> dict:
            """List exported figures, inspect exact plotted-array metadata, or read a bounded page.
            Empty name lists figures; name returns array IDs and source sections; array reads values.
            Raw recording paths and voltage files are never exposed.
            """
            return queries.figure_data(name, array, offset, limit)

        @mcp.tool()
        def search_project_conversation(query: str = "", limit: int = 10) -> dict:
            """Find earlier questions and answers saved in this project only."""
            return queries.history(query, limit)

        @mcp.tool()
        def search_app_guidance(query: str, language: str = "zh_CN", limit: int = 3) -> dict:
            """Search the built-in app tutorial for real controls, prerequisites, checks and outputs.
            Use this before giving step-by-step NeuroEphys AI instructions. No project data is read.
            """
            return queries.guidance(query, language, limit)

        @mcp.tool()
        def propose_analysis_action(name: str, arguments: dict[str, Any], reason: str = "") -> dict:
            """Propose a registered app action. Never executes; app asks for confirmation.
            Obtain valid action names/parameters with list_project_data first.
            """
            return queries.propose(name, arguments, reason)

        inner = mcp.streamable_http_app()
        expected = ("Bearer " + self.token).encode()

        async def authenticated(scope, receive, send):
            if scope["type"] == "http":
                headers = dict(scope.get("headers", []))
                if not hmac.compare_digest(headers.get(b"authorization", b""), expected):
                    await send({"type": "http.response.start", "status": 401, "headers": []})
                    await send({"type": "http.response.body", "body": b"Unauthorized"})
                    return
            await inner(scope, receive, send)

        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen(16)
        self.url = f"http://127.0.0.1:{self.socket.getsockname()[1]}/mcp"
        self.server = uvicorn.Server(uvicorn.Config(authenticated, log_level="critical", log_config=None,
                                                   access_log=False, ws="none", lifespan="on"))
        self.thread = threading.Thread(target=lambda: self.server.run(sockets=[self.socket]), daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() > deadline:
                self.__exit__(None, None, None)
                raise RuntimeError("Project query service could not start.")
            time.sleep(0.02)
        return self

    def __exit__(self, *_):
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=5)
        if self.socket:
            self.socket.close()
