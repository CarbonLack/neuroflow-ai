from __future__ import annotations

from typing import Any

KNOWLEDGE_VERSION = "2026-07-28"

SOURCES: tuple[dict[str, Any], ...] = (
    {
        "id": "spikeinterface-overview",
        "title": "SpikeInterface documentation",
        "url": "https://spikeinterface.readthedocs.io/en/stable/",
        "stages": ["import", "qc", "preprocess", "sorting", "unit_qc"],
        "source_type": "official_documentation",
    },
    {
        "id": "spikeinterface-sorters",
        "title": "SpikeInterface spike sorters module",
        "url": "https://spikeinterface.readthedocs.io/en/stable/modules/sorters.html",
        "stages": ["sorting"],
        "source_type": "official_documentation",
    },
    {
        "id": "spikeinterface-qualitymetrics",
        "title": "SpikeInterface quality metrics",
        "url": "https://spikeinterface.readthedocs.io/en/stable/modules/metrics/quality_metrics.html",
        "stages": ["unit_qc"],
        "source_type": "official_documentation",
    },
    {
        "id": "kilosort4-docs",
        "title": "Kilosort4 documentation",
        "url": "https://kilosort.readthedocs.io/en/latest/",
        "stages": ["sorting", "unit_qc"],
        "source_type": "official_documentation",
    },
    {
        "id": "mountainsort5-docs",
        "title": "MountainSort5 documentation",
        "url": "https://github.com/flatironinstitute/mountainsort5",
        "stages": ["sorting", "unit_qc"],
        "source_type": "official_repository",
    },
    {
        "id": "elephant-docs",
        "title": "Elephant documentation",
        "url": "https://elephant.readthedocs.io/en/latest/",
        "stages": ["analysis", "statistics"],
        "source_type": "official_documentation",
    },
    {
        "id": "neo-docs",
        "title": "Neo documentation",
        "url": "https://neo.readthedocs.io/en/latest/",
        "stages": ["import", "analysis"],
        "source_type": "official_documentation",
    },
    {
        "id": "nwb-docs",
        "title": "Neurodata Without Borders documentation",
        "url": "https://www.nwb.org/",
        "stages": ["import", "export"],
        "source_type": "official_documentation",
    },
    {
        "id": "deepseek-chat-api",
        "title": "DeepSeek Chat Completions API",
        "url": "https://api-docs.deepseek.com/api/create-chat-completion",
        "stages": list(
            (
                "import",
                "qc",
                "preprocess",
                "sorting",
                "unit_qc",
                "sync",
                "behavior",
                "analysis",
                "statistics",
                "decoding",
                "export",
            )
        ),
        "source_type": "official_documentation",
    },
    {
        "id": "deepseek-tool-calls",
        "title": "DeepSeek tool calls",
        "url": "https://api-docs.deepseek.com/guides/tool_calls",
        "stages": list(
            (
                "import",
                "qc",
                "preprocess",
                "sorting",
                "unit_qc",
                "sync",
                "behavior",
                "analysis",
                "statistics",
                "decoding",
                "export",
            )
        ),
        "source_type": "official_documentation",
    },
)


def sources_for_stage(stage: str) -> dict[str, Any]:
    return {
        "version": KNOWLEDGE_VERSION,
        "sources": [
            source
            for source in SOURCES
            if stage in source.get("stages", [])
        ],
    }
