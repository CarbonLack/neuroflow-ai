from __future__ import annotations

import asyncio
import json

import httpx
import numpy as np
import pytest

from neuroflow.ai_project_bridge import ProjectQueries, ProjectMCPBridge
from neuroflow.models import ProjectState
from neuroflow.project import save_ai_conversation, restore_ai_conversation


def project(tmp_path):
    state = ProjectState(root=tmp_path, channel_count=32, duration_seconds=1200)
    state.events = [{"event_code": 11 if i % 2 else 5, "time": i / 2} for i in range(150)]
    state.unit_metrics = [{"unit_id": i, "snr": 2 + i / 10} for i in range(70)]
    state.sorted_spikes = {7: np.array([1.1, 1.4, 2.7])}
    state.metadata["ai_history"] = [{"question": "Use animal-level validation", "answer": "Agreed"}]
    state.analysis = {"psth": {"values": np.arange(250)}}
    return state


def test_pages_filters_deep_results_and_snapshot_isolation(tmp_path):
    state = project(tmp_path)
    queries = ProjectQueries(state, "analysis", "assistant")
    state.events[1]["time"] = 999
    page = queries.query("events", filters={"event_code": 11}, offset=1, limit=2)["result"]
    assert page["total"] == 75
    assert [r["time"] for r in page["data"]] == [1.5, 2.5]
    assert page["next_offset"] == 3
    metric = queries.query("unit_metrics", filters={"unit_id": 65})["result"]
    assert metric["data"][0]["snr"] == 8.5
    nested = queries.query("analysis", ["psth", "values"], offset=200, limit=3)["result"]
    assert nested["data"] == [200, 201, 202]
    spikes = queries.query("sorted_spikes", ["7"])["result"]
    assert spikes["data"] == [1.1, 1.4, 2.7]
    assert queries.audit[-1]["result"] == spikes


def test_queries_do_not_expose_raw_or_credentials(tmp_path):
    state = project(tmp_path)
    state.metadata["api_key"] = "secret"
    state.metadata["source_path"] = str(tmp_path / "private.bin")
    queries = ProjectQueries(state, "import", "assistant")
    result = json.dumps(queries.query("metadata"))
    assert '"api_key"' not in result
    assert "private.bin" not in result
    for section in ("recording_path", "ground_truth"):
        with pytest.raises(ValueError):
            queries.query(section)
    with pytest.raises(ValueError):
        queries.query("metadata", ["api_key"])
    queries.allowed_sections = set()
    with pytest.raises(ValueError):
        queries.query("events")
    with pytest.raises(ValueError):
        queries.history()


def test_history_survives_reopen_and_does_not_mix_projects(tmp_path):
    first = project(tmp_path / "first")
    save_ai_conversation(first)
    reopened = ProjectState(root=first.root)
    restore_ai_conversation(reopened)
    assert ProjectQueries(reopened, "import", "assistant").history("animal-level")["result"]
    assert ProjectQueries(reopened, "import", "assistant").history("animal-level unrelated validation")["result"]
    other = ProjectState(root=tmp_path / "second")
    assert ProjectQueries(other, "import", "assistant").history("animal-level")["result"] == []


def test_actions_are_validated_proposals_not_execution(tmp_path):
    state = project(tmp_path)
    queries = ProjectQueries(state, "analysis", "collaborative")
    result = queries.propose("compute_unit_qc", {}, "Review candidates")["result"]
    assert result["executed"] is False
    assert result["status"] == "awaiting_user_confirmation"
    assert not state.workflow_status
    with pytest.raises(ValueError):
        queries.propose("shell", {"command": "anything"})
    with pytest.raises(ValueError):
        queries.propose("compute_unit_qc", {"unexpected": True})
    with pytest.raises(ValueError):
        ProjectQueries(state, "analysis", "assistant").propose("compute_unit_qc", {})


def test_real_mcp_protocol_authentication_and_query(tmp_path):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    queries = ProjectQueries(project(tmp_path), "analysis", "assistant")
    with ProjectMCPBridge(queries) as bridge:
        assert httpx.post(bridge.url, json={"method": "tools/list"}).status_code == 401

        async def use_client():
            async with streamablehttp_client(bridge.url, headers={"Authorization": "Bearer " + bridge.token}) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert "query_project_data" in [t.name for t in tools.tools]
                    assert "search_app_guidance" in [t.name for t in tools.tools]
                    result = await session.call_tool("query_project_data", {
                        "section": "unit_metrics", "filters": {"unit_id": 65}})
                    assert not result.isError
                    data = json.loads(result.content[0].text)
                    assert data["result"]["data"][0]["snr"] == 8.5
                    guidance = await session.call_tool("search_app_guidance", {
                        "query": "sorting", "language": "en_US"})
                    assert not guidance.isError
                    assert json.loads(guidance.content[0].text)["result"]["guides"]
        asyncio.run(use_client())
    assert not bridge.thread.is_alive()
