from __future__ import annotations

import json
import base64
import ipaddress
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

from .ai_credentials import get_api_key
from .ai_tools import AIMode, TOOL_REGISTRY, provider_tools
from .knowledge_base import sources_for_stage
from .models import ProjectState
from .product import PRODUCT_NAME, PRODUCT_VERSION
from .unit_curation import curation_summary

WORKFLOW_STAGES = (
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

STAGE_LABELS = {
    "zh_CN": {
        "import": "数据与项目",
        "qc": "原始质控",
        "preprocess": "预处理",
        "sorting": "Spike sorting",
        "unit_qc": "Unit 质控",
        "sync": "事件同步",
        "behavior": "行为分析",
        "analysis": "神经活动分析",
        "statistics": "统计检验",
        "decoding": "机器学习与神经解码",
        "export": "论文与复现",
    },
    "en_US": {
        "import": "Data and project",
        "qc": "Raw QC",
        "preprocess": "Preprocessing",
        "sorting": "Spike sorting",
        "unit_qc": "Unit QC",
        "sync": "Event synchronization",
        "behavior": "Behavior analysis",
        "analysis": "Neural analysis",
        "statistics": "Statistical testing",
        "decoding": "Machine learning and decoding",
        "export": "Publication and reproducibility",
    },
}

AI_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "stage": {
                        "type": "string",
                        "enum": list(WORKFLOW_STAGES),
                    },
                    "reason": {"type": "string"},
                    "prerequisites": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "recommended_parameters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                                "rationale": {"type": "string"},
                            },
                            "required": ["name", "value", "rationale"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "stage",
                    "reason",
                    "prerequisites",
                    "recommended_parameters",
                ],
                "additionalProperties": False,
            },
        },
        "suggested_next_stage": {
            "type": "string",
            "enum": list(WORKFLOW_STAGES),
        },
        "requires_user_confirmation": {"type": "boolean"},
        "tool_calls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": list(TOOL_REGISTRY),
                    },
                    "arguments": {"type": "object"},
                    "reason": {"type": "string"},
                },
                "required": ["name", "arguments", "reason"],
                "additionalProperties": False,
            },
        },
        "scientific_interpretation": {
            "type": "object",
            "properties": {
                "observed_results": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "statistical_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "possible_interpretations": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "unsupported_conclusions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "limitations": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "suggested_validation": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "observed_results",
                "statistical_evidence",
                "possible_interpretations",
                "unsupported_conclusions",
                "limitations",
                "suggested_validation",
            ],
            "additionalProperties": False,
        },
    },
    "required": [
        "answer",
        "warnings",
        "plan",
        "suggested_next_stage",
        "requires_user_confirmation",
    ],
    "additionalProperties": False,
}


class AIConfigurationError(ValueError):
    """Raised when the configured provider cannot make a safe request."""


class AIRequestError(RuntimeError):
    """Raised when a remote model request fails or returns unusable output."""


PROVIDER_PROFILES: dict[str, dict[str, Any]] = {
    "harness_sdk": {
        "label": "DeepSeek Harness · SDK + project tools",
        "base_url": "harness://local",
        "models": [],
        "api_style": "harness_sdk",
    },
    "deepseek": {
        "label": "DeepSeek API",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "api_style": "chat",
    },
    "openai_responses": {
        "label": "OpenAI Responses API",
        "base_url": "https://api.openai.com/v1",
        "models": [],
        "api_style": "responses",
    },
    "openai_compatible": {
        "label": "OpenAI-compatible service",
        "base_url": "http://127.0.0.1:11434/v1",
        "models": [],
        "api_style": "chat",
    },
    "ollama": {
        "label": "Ollama · local computer",
        "base_url": "http://127.0.0.1:11434/v1",
        "models": ["qwen3:8b", "qwen3:4b", "deepseek-r1:8b"],
        "api_style": "chat",
        "local": True,
    },
    "private_compatible": {
        "label": "Laboratory/private compatible service",
        "base_url": "https://model-server.example/v1",
        "models": [],
        "api_style": "chat",
    },
    "institute_harness": {
        "label": "Institute model harness · OpenAI-compatible",
        "base_url": "https://model-harness.example/v1",
        "models": [],
        "api_style": "chat",
        "managed": True,
    },
}


def supports_image_input(provider: str) -> bool:
    """Whether this transport can carry a PNG; model capability is checked remotely."""
    return provider in {
        "harness_sdk", "openai_responses", "openai_compatible",
        "private_compatible", "institute_harness",
    }


@dataclass(slots=True)
class AISettings:
    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    mode: str = AIMode.ASSISTANT.value
    reasoning_effort: str = "medium"
    timeout_seconds: int = 90
    retry_count: int = 2
    stream: bool = True
    include_recent_log: bool = False
    selected_context_fields: list[str] = field(default_factory=list)
    safety_identifier: str = ""
    api_key_env: str = ""
    allow_insecure_private_network: bool = False
    managed_harness_name: str = ""
    harness_provider: str = ""
    api_key: str = field(
        default="",
        repr=False,
    )

    @property
    def configured(self) -> bool:
        if self.provider == "harness_sdk":
            import shutil
            return bool(self.model.strip() and self.harness_provider.strip() and shutil.which("dsh"))
        credentials_ready = bool(self.request_api_key)
        return bool(
            credentials_ready and self.base_url.strip() and self.model.strip()
        )

    @property
    def request_api_key(self) -> str:
        if self.provider == "harness_sdk":
            return ""
        if self.api_key.strip():
            return self.api_key.strip()
        environment_key = get_api_key(
            self.provider,
            self.api_key_env,
        )
        if environment_key:
            return environment_key
        if PROVIDER_PROFILES.get(self.provider, {}).get("local"):
            return "ollama"
        return ""

    @property
    def provider_label(self) -> str:
        return PROVIDER_PROFILES.get(self.provider, {}).get(
            "label",
            self.provider,
        )

    @property
    def ai_mode(self) -> AIMode:
        try:
            return AIMode(self.mode)
        except ValueError:
            return AIMode.ASSISTANT


@dataclass(slots=True)
class AIResponse:
    answer: str
    warnings: list[str]
    plan: list[dict[str, Any]]
    suggested_next_stage: str
    requires_user_confirmation: bool
    model: str
    provider: str
    response_id: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    scientific_interpretation: dict[str, list[str]] = field(
        default_factory=dict
    )
    sent_field_categories: list[str] = field(default_factory=list)
    query_evidence: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def audit_record(self, question: str, task: str) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "task": task,
            "question": redact_sensitive_text(question),
            "answer": redact_sensitive_text(self.answer),
            "warnings": [
                redact_sensitive_text(item) for item in self.warnings
            ],
            "plan": self.plan,
            "suggested_next_stage": self.suggested_next_stage,
            "requires_user_confirmation": self.requires_user_confirmation,
            "provider": self.provider,
            "model": self.model,
            "response_id": self.response_id,
            "usage": self.usage,
            "tool_calls": self.tool_calls,
            "scientific_interpretation": self.scientific_interpretation,
            "sent_field_categories": self.sent_field_categories,
            "query_evidence": self.query_evidence,
            "online_request_authorized": True,
            "result_purpose": task,
            "raw_voltage_sent": False,
            "local_paths_sent": False,
            "api_key_recorded": False,
        }


def _compact_json_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 3:
        return "<nested value omitted>"
    if isinstance(value, dict):
        return {
            str(key): _compact_json_value(item, depth=depth + 1)
            for key, item in list(value.items())[:24]
            if not any(
                token in str(key).lower()
                for token in ("path", "file", "name", "subject", "animal", "mouse")
            )
        }
    if isinstance(value, (list, tuple)):
        return [
            _compact_json_value(item, depth=depth + 1) for item in list(value)[:20]
        ]
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _multi_session_registry_summary(state: ProjectState) -> dict[str, Any]:
    """Expose scientific status and counts, never study names, IDs within rows, or paths."""
    registry = state.metadata.get("multi_session_studies", {})
    if not isinstance(registry, dict):
        return {}
    allowed = {
        "study_id",
        "status",
        "animal_count",
        "session_count",
        "selected_conditions",
        "model",
        "group_by",
        "balanced_accuracy",
        "roc_auc",
        "permutation_p",
        "hierarchical_condition_effect",
        "latent_dynamics",
        "safeguards",
    }
    summary: dict[str, Any] = {}
    for study_id, entry in list(registry.items())[:20]:
        if not isinstance(entry, dict):
            continue
        safe_entry = {key: entry[key] for key in allowed if key in entry}
        summary[str(study_id)[:64]] = _compact_json_value(safe_entry)
        # Counts are scientifically necessary and not identifying values. The generic
        # metadata redactor intentionally removes animal-like keys, so restore only counts.
        for key in ("animal_count", "session_count"):
            if key in entry:
                summary[str(study_id)[:64]][key] = int(entry[key])
    return summary


def _normalized_acquisition_settings(state: ProjectState) -> dict[str, Any]:
    """Merge legacy and current acquisition metadata into a path-free summary."""
    legacy = state.metadata.get("acquisition", {})
    preprocessing = state.metadata.get("acquisition_preprocessing", {})
    merged = {
        **(legacy if isinstance(legacy, dict) else {}),
        **(preprocessing if isinstance(preprocessing, dict) else {}),
    }
    filters = merged.get("online_filters", [])
    if isinstance(filters, list) and filters:
        low_cuts = [
            float(item["low_cut_hz"])
            for item in filters
            if isinstance(item, dict) and item.get("low_cut_hz") is not None
        ]
        high_cuts = [
            float(item["high_cut_hz"])
            for item in filters
            if isinstance(item, dict) and item.get("high_cut_hz") is not None
        ]
        if low_cuts and merged.get("online_highpass_hz") is None:
            merged["online_highpass_hz"] = min(low_cuts)
        if high_cuts and merged.get("online_lowpass_hz") is None:
            merged["online_lowpass_hz"] = max(high_cuts)
    return _compact_json_value(merged)


def _stage_run_summary(state: ProjectState) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in state.metadata.get("structured_run_log", [])[-30:]:
        if not isinstance(item, dict) or item.get("status") == "running":
            continue
        records.append(
            _compact_json_value(
                {
                    "run_id": str(item.get("run_id", ""))[:12],
                    "stage": item.get("stage"),
                    "tool": item.get("tool"),
                    "tool_version": item.get("tool_version"),
                    "parameters": item.get("parameters", {}),
                    "channel_selection": item.get("channel_selection"),
                    "segment": item.get("segment", {}),
                    "elapsed_seconds": item.get("elapsed_seconds"),
                    "status": item.get("status"),
                    "warning_count": len(item.get("warnings", [])),
                    "error_type": (
                        item.get("error", {}).get("type")
                        if isinstance(item.get("error"), dict)
                        else None
                    ),
                    "error_message": (
                        redact_sensitive_text(
                            str(item.get("error", {}).get("message", ""))
                        )[:800]
                        if isinstance(item.get("error"), dict)
                        else None
                    ),
                    "artifact_ids": [
                        artifact.get("id")
                        for artifact in item.get("artifacts", [])[:30]
                        if isinstance(artifact, dict)
                    ],
                    "recovery": item.get("recovery"),
                }
            )
        )
    return records


def _event_inventory(state: ProjectState) -> dict[str, Any]:
    configured = state.metadata.get("event_inventory")
    if isinstance(configured, dict) and configured:
        return _compact_json_value(configured)
    by_code: dict[str, dict[str, Any]] = {}
    for event in state.events:
        code = str(event.get("event_code", "unmapped"))
        entry = by_code.setdefault(
            code,
            {
                "label": str(
                    event.get("label", event.get("condition", f"event_{code}"))
                ),
                "count": 0,
            },
        )
        entry["count"] += 1
    return _compact_json_value(
        {
            "total_events": len(state.events),
            "task_events": sum(
                event.get("analysis_role") == "task_event"
                for event in state.events
            ),
            "synchronization_events": sum(
                event.get("analysis_role") == "synchronization"
                for event in state.events
            ),
            "by_code": by_code,
        }
    )


def build_project_summary(
    state: ProjectState | None,
    current_step: str,
    *,
    include_recent_log: bool = False,
) -> dict[str, Any]:
    """Build a small, path-free summary suitable for an optional cloud model."""
    if state is None:
        return {
            "project_open": False,
            "current_stage": current_step,
            "allowed_stages": list(WORKFLOW_STAGES),
        }

    sorting_units = {}
    for sorter, spikes_by_unit in state.sorting_results.items():
        provenance = state.sorting_provenance.get(sorter, {})
        sorting_units[sorter] = {
            "unit_count": len(spikes_by_unit),
            "spike_count": int(
                sum(len(spikes) for spikes in spikes_by_unit.values())
            ),
            "version": provenance.get("version"),
            "parameters": _compact_json_value(provenance.get("parameters", {})),
            "runtime_seconds": provenance.get(
                "runtime_seconds",
                provenance.get("elapsed_seconds"),
            ),
        }
    acquisition = _normalized_acquisition_settings(state)
    probe = _compact_json_value(
        {
            "electrode_type": state.electrode_type,
            **state.metadata.get("probe", {}),
            "brain_region": state.metadata.get("brain_region"),
            "reference": state.metadata.get("reference"),
            "known_bad_channels": state.metadata.get("known_bad_channels", []),
        }
    )
    selected_unit_metrics = [
        _compact_json_value(item) for item in state.unit_metrics[:50]
    ]
    sync_summary = _compact_json_value(
        state.metadata.get(
            "synchronization",
            state.analysis.get("synchronization", {}),
        )
    )
    ui_context = _compact_json_value(state.metadata.get("ui_context", {}))
    artifacts = [
        _compact_json_value(
            {
                "id": item.get("id"),
                "stage": item.get("stage"),
                "kind": item.get("kind"),
                "status": item.get("status"),
                "label": item.get("label"),
                "size_bytes": item.get("size_bytes"),
                "sha256": item.get("sha256"),
                "tool": item.get("tool"),
            }
        )
        for item in state.metadata.get("artifacts", [])[-50:]
    ]
    summary: dict[str, Any] = {
        "project_open": True,
        "context_schema": "neuroephys.cloud-project-summary.v2",
        "application_contract": {
            "product": "NeuroEphys AI",
            "workflow_order": list(WORKFLOW_STAGES),
            "current_stage": current_step,
            "advice_is_non_executing": True,
            "tool_calls_require_registry_validation": True,
            "high_risk_actions_require_confirmation": True,
            "raw_voltage_is_never_embedded": True,
            "local_paths_are_redacted": True,
        },
        "source_type": state.source_type,
        "recording_system": state.metadata.get(
            "recording_system",
            state.source_type,
        ),
        "source_linked_locally": bool(state.source_path or state.recording_path),
        "electrode_type": state.electrode_type,
        "sampling_rate_hz": state.sampling_rate,
        "channel_count": state.channel_count,
        "duration_seconds": state.duration_seconds,
        "dtype": state.dtype,
        "signal_unit": state.metadata.get("signal_unit", "unknown"),
        "acquisition_settings": acquisition,
        "probe_and_recording_metadata": probe,
        "event_count": len(state.events),
        "trial_count": len(state.trials),
        "trial_definition": _compact_json_value(
            state.metadata.get(
                "trial_definition",
                {
                    "status": "defined" if state.trials else "not_defined",
                    "trial_count": len(state.trials),
                },
            )
        ),
        "event_inventory": _event_inventory(state),
        "data_preview": {
            "events": _compact_json_value(state.events[:20]),
            "trials": _compact_json_value(state.trials[:10]),
            "scope": "Bounded samples, not the full dataset; times retain their stored units.",
        },
        "recent_operations": [redact_sensitive_text(str(item)) for item in state.run_log[-15:]],
        "synchronization_summary": sync_summary,
        "sorting_results": {
            sorter: details["unit_count"]
            for sorter, details in sorting_units.items()
        },
        "sorting_details": sorting_units,
        "active_sorter": state.active_sorter_key,
        "active_unit_count": len(state.sorted_spikes),
        "workflow_status": {
            stage: state.workflow_status.get(stage, "pending")
            for stage in WORKFLOW_STAGES
        },
        "current_stage": current_step,
        "qc_summary": _compact_json_value(state.qc),
        "preprocessing_summary": _compact_json_value(state.preprocessing),
        "unit_metric_count": len(state.unit_metrics),
        "unit_metrics": selected_unit_metrics,
        "unit_curation": curation_summary(state),
        "external_observations": _compact_json_value(
            state.metadata.get("external_observations", [])
        ),
        "analysis_summary": _compact_json_value(state.analysis),
        "spike_train_summary": _compact_json_value(
            state.spike_train_analysis
        ),
        "lfp_summary": _compact_json_value(state.lfp_analysis),
        "spike_field_summary": _compact_json_value(
            state.spike_field_analysis
        ),
        "statistics_summary": _compact_json_value(state.statistics),
        "decoding_summary": _compact_json_value(state.decoding),
        "decoding_input_diagnostics": _compact_json_value(
            state.metadata.get("decoding_input_diagnostics", {})
        ),
        "regression_summary": _compact_json_value(state.regression),
        "multi_session_studies": _multi_session_registry_summary(state),
        "current_ui_context": ui_context,
        "artifact_inventory": artifacts,
        "recent_stage_runs": _stage_run_summary(state),
        "knowledge_sources": sources_for_stage(current_step),
        "failed_or_skipped_steps": [
            {
                "stage": stage,
                "status": status,
            }
            for stage, status in state.workflow_status.items()
            if status in {"failed", "skipped", "blocked"}
        ],
        "allowed_stages": list(WORKFLOW_STAGES),
    }
    if include_recent_log:
        summary["recent_log"] = [
            redact_sensitive_text(item) for item in state.run_log[-5:]
        ]
    return summary


def build_local_project_context(
    state: ProjectState | None,
    current_step: str,
    *,
    include_recent_log: bool = False,
) -> dict[str, Any]:
    context = build_project_summary(
        state,
        current_step,
        include_recent_log=include_recent_log,
    )
    if state is None:
        return context
    context["local_only"] = {
        "project_root": str(state.root),
        "source_path": str(state.source_path) if state.source_path else None,
        "recording_path": (
            str(state.recording_path) if state.recording_path else None
        ),
    }
    return context


def select_cloud_context(
    summary: dict[str, Any],
    selected_fields: list[str] | None,
) -> dict[str, Any]:
    if not selected_fields:
        return {
            key: value
            for key, value in summary.items()
            if key != "local_only"
        }
    always = {
        "project_open",
        "context_schema",
        "current_stage",
        "allowed_stages",
    }
    selected = set(selected_fields) | always
    return {
        key: value
        for key, value in summary.items()
        if key in selected and key != "local_only"
    }


_WINDOWS_PATH = re.compile(r"(?i)\b[A-Z]:\\(?:[^\\\r\n]+\\)*[^\\\r\n]*")
_UNIX_PATH = re.compile(r"(?<!\w)/(?:[^/\s]+/)+[^/\s]*")
_API_KEY = re.compile(r"\b(?:sk|sess)-[A-Za-z0-9_-]{12,}\b")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def redact_sensitive_text(text: str) -> str:
    redacted = _WINDOWS_PATH.sub("<local-path-redacted>", str(text))
    redacted = _UNIX_PATH.sub("<local-path-redacted>", redacted)
    redacted = _API_KEY.sub("<api-key-redacted>", redacted)
    return _EMAIL.sub("<email-redacted>", redacted)


def build_response_style_contract(language: str) -> str:
    """Return one provider-independent contract for clear, low-burden replies."""
    if language == "zh_CN":
        return """
回答应像一位耐心、可靠的科研同事，而不是字段说明书或运行日志。

表达规则：
1. 先直接回答用户真正问的问题。第一段用一到两句话说清结论；不要用“我来解释一下”开场。
2. 随后只保留理解结论所必需的信息。优先使用以下自然结构，并省略不适用的小节：
   - **结论**：这代表什么，当前能不能做出判断。
   - **为什么**：最多三点，每一点都要把项目证据翻译成科研含义。
   - **你现在可以怎么做**：只有存在有用操作时才给出，步骤必须具体且可执行。
   - **需要注意**：只放会改变判断的重要限制或风险。
3. 不要把内部字段、数组、JSON、工具名或参数列表直接倾倒给用户。首次需要提到内部名称时，先写中文含义，再在括号中写一次字段名；之后只用中文含义。例如写“线路噪声通道（line_noise_channel）”，不要逐字段朗读 qc_summary。
4. 每个数字都说明对象、单位和意义。明确区分“当前项目实际观察”“软件默认值”“一般方法知识”和“尚未取得的证据”。
5. 简单问题通常用 120–300 个汉字；结果解释或操作指导通常用 300–700 个汉字。清晰度优先于机械限字。用户明确要求详细时可以更长，但仍先给简短结论，再分层展开。
6. 只在确有必要时使用项目符号；一个要点只表达一件事。不要重复用户问题、界面上下文或已经说过的结论。
7. 如果信息不足，明确说“目前还不能判断”，紧接着说明缺哪一项证据以及怎样获得；不要用大段背景知识掩盖缺失信息。
8. 用户问某个图、指标或字段时，回答顺序为：它是什么 → 当前值/图说明什么 → 是否异常或可用 → 下一步怎么确认。用户没有要求时，不扩展到无关模块。
9. 不叙述内部推理、MCP/工具管线、查询语法、原始日志或隐私信息。可以给出简洁、可核查的依据。
""".strip()
    return """
Write like a patient, reliable research colleague, not a schema reference or run log.

Response rules:
1. Answer the user's real question first. State the conclusion in one or two sentences; do not open with meta-commentary.
2. Keep only information needed to understand or act on the conclusion. Use these natural sections when relevant and omit empty ones: **Conclusion**, **Why**, **What to do now**, and **Important limitation**.
3. Do not dump internal fields, arrays, JSON, tool names, or parameter lists. Translate an internal identifier into plain scientific language and show the identifier in parentheses only once when it is genuinely useful.
4. Give every number an object, unit, and meaning. Distinguish current-project observations, software defaults, general method knowledge, and evidence that has not yet been obtained.
5. A simple answer is usually 60–120 words; a result explanation or procedure is usually 120–220 words. Clarity outranks a mechanical word cap. If detail is explicitly requested, expand after a concise conclusion.
6. Use bullets only when they improve scanning; one point should carry one idea. Do not repeat the question, UI context, or conclusion.
7. If evidence is insufficient, say so directly, then name the missing evidence and how to obtain it.
8. For a plot, metric, or field, answer in this order: what it is, what the current value/plot means, whether it is usable or concerning, and how to confirm it. Do not expand into unrelated modules.
9. Do not narrate private reasoning, MCP/tool plumbing, query syntax, raw logs, or private information. Provide concise, checkable evidence instead.
""".strip()


def build_system_instructions(
    language: str,
    task: str,
    mode: AIMode | str = AIMode.ASSISTANT,
) -> str:
    output_language = "Simplified Chinese" if language == "zh_CN" else "English"
    mode_value = str(mode)
    response_style = build_response_style_contract(language)
    return f"""
You are {PRODUCT_NAME}'s controlled electrophysiology assistant. Reply in {output_language}.

The active AI mode is {mode_value}. Numerical calculation is performed by registered
deterministic local modules. You explain evidence, diagnose risks, propose editable
workflows and, only in collaborative mode, may request a registered local tool.

Hard boundaries:
1. Never claim that a step ran, a unit is biologically valid, or a scientific
   hypothesis is proven unless the supplied project summary contains that evidence.
2. Never invent a channel, event, unit, effect size, p-value, model score, file, or
   software result.
3. Keep raw QC, preprocessing, spike sorting, Unit QC, synchronization, statistics,
   and interpretation distinct. State missing prerequisites explicitly.
4. A proposed plan may use only these stage keys:
   {", ".join(WORKFLOW_STAGES)}.
5. A tool request may use only these exact tool names:
   {", ".join(TOOL_REGISTRY)}.
6. In manual mode, do not answer with a tool call. In assistant mode, provide
   explanation and workflow advice only. In collaborative mode, return a tool call
   only when it materially advances the user's explicit request.
7. Every tool call remains a proposal. Sorting, long tasks, result replacement,
   batch execution, exports and any network transfer require local validation and
   an explicit user confirmation dialog.
8. AI advice is optional. Important parameters and scientific interpretation require
   user review.
9. Do not request raw voltage or identifying metadata. Work only from the supplied
   minimal structured summary.
10. Distinguish a default starting point from a universally correct parameter.
    Explain why a recommendation fits the supplied recording and what the user must
    inspect.
11. Candidate clusters remain candidate Units until manual curation. Sorter count
    disagreements do not establish which result is correct.
12. For scientific interpretation, separately report: observed results, statistical
    evidence, possible biological interpretations, unsupported conclusions, data and
    method limitations, and suggested validation. Do not turn association into
    causation. Preserve animal/session/unit hierarchy and report nonsignificant
    results directly.
13. You may answer general scientific and everyday questions from model knowledge.
    Distinguish this from verified project evidence. Do not invent citations or claim
    that a current external fact was checked without an actual source lookup.
14. The current task type is {task!r}. Return the required JSON object with no
    markdown code fence.
15. In a multi-session study, preserve trial -> session -> animal hierarchy. Never
    treat equal Unit IDs across sessions as the same cell without explicit tracking
    evidence, never call session-held-out validation cross-animal validation, and
    distinguish supervised LDA from the separate descriptive latent-dynamics model.

Conversation behavior:
Answer the user's actual question directly, including open-ended discussion of
this project, methods, data contents, existing results, general neuroscience,
software operation, and other topics. Do not force every
conversation into a workflow plan. Use current_ui_context, data_preview,
recent_operations and all available result summaries as evidence. The supplied
snapshot is fresh for this request. Missing fields are unknown, not zero.
Recent conversation belongs to this project; do not claim access to other projects.
An inspect_project or summarize_recording call is unnecessary when the supplied
snapshot already answers the question. Always provide a substantive answer.

Reading and explanation contract:
{response_style}
Mention project evidence reads and proposed actions only as a short status. Preserve
uncertainty and safety-critical warnings. Never expose private chain-of-thought.

Required response format (answer must contain your actual response):
{{"answer":"Your response in {output_language}","warnings":[],"plan":[],
"suggested_next_stage":"import","requires_user_confirmation":false,
"tool_calls":[]}}
Only populate plan or tool_calls when relevant. Any tool arguments must match
the registered tool schema. Scientific interpretation may be supplied separately.
""".strip()


def build_user_input(
    question: str,
    project_summary: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> str:
    safe_history = []
    for item in (history or [])[-40:]:
        role = "assistant" if item.get("role") == "assistant" else "user"
        safe_history.append(
            {"role": role, "content": redact_sensitive_text(item.get("content", ""))}
        )
    payload = {
        "question": redact_sensitive_text(question),
        "project_summary": project_summary,
        "recent_conversation": safe_history,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _endpoint(base_url: str, suffix: str) -> str:
    base = base_url.strip().rstrip("/")
    if base.endswith(suffix):
        return base
    return f"{base}/{suffix.lstrip('/')}"


def _validate_endpoint(
    url: str,
    *,
    allow_insecure_private_network: bool = False,
) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        return
    if parsed.scheme == "http" and allow_insecure_private_network:
        try:
            address = ipaddress.ip_address(str(parsed.hostname))
        except ValueError:
            address = None
        if address and (address.is_private or address.is_link_local):
            return
    raise AIConfigurationError(
        "The AI endpoint must use HTTPS. Plain HTTP is allowed only for localhost "
        "or an explicitly approved private-network harness."
    )


def _post_json(
    url: str,
    payload: dict[str, Any],
    api_key: str,
    timeout_seconds: int,
    retry_count: int = 0,
    *,
    allow_insecure_private_network: bool = False,
) -> dict[str, Any]:
    _validate_endpoint(
        url,
        allow_insecure_private_network=allow_insecure_private_network,
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"{PRODUCT_NAME}/{PRODUCT_VERSION}",
        },
    )
    attempts = max(0, int(retry_count)) + 1
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(
                request,
                timeout=max(10, int(timeout_seconds)),
                context=ssl.create_default_context(),
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(details)
                details = parsed.get("error", {}).get("message", details)
            except json.JSONDecodeError:
                pass
            transient = exc.code in {408, 409, 425, 429} or exc.code >= 500
            if transient and attempt + 1 < attempts:
                time.sleep(min(0.75 * (2**attempt), 4.0))
                continue
            raise AIRequestError(
                f"AI service returned HTTP {exc.code}: {details}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt + 1 < attempts:
                time.sleep(min(0.75 * (2**attempt), 4.0))
                continue
            if isinstance(exc, urllib.error.URLError):
                raise AIRequestError(
                    f"Cannot reach the AI service: {exc.reason}"
                ) from exc
            raise AIRequestError("The AI request timed out.") from exc
        except json.JSONDecodeError as exc:
            raise AIRequestError(
                "The AI service returned invalid JSON."
            ) from exc
    raise AIRequestError("The AI request failed after retrying.")


def _post_chat_stream(
    url: str,
    payload: dict[str, Any],
    api_key: str,
    timeout_seconds: int,
    *,
    on_text: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    allow_insecure_private_network: bool = False,
) -> dict[str, Any]:
    _validate_endpoint(
        url,
        allow_insecure_private_network=allow_insecure_private_network,
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": f"{PRODUCT_NAME}/{PRODUCT_VERSION}",
        },
    )
    content_parts: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}
    response_id = ""
    usage: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(
            request,
            timeout=max(10, int(timeout_seconds)),
            context=ssl.create_default_context(),
        ) as response:
            for raw_line in response:
                if cancel_event and cancel_event.is_set():
                    raise AIRequestError("The AI request was cancelled.")
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                response_id = response_id or str(chunk.get("id", ""))
                if chunk.get("usage"):
                    usage = chunk["usage"]
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                text = delta.get("content")
                if isinstance(text, str) and text:
                    content_parts.append(text)
                    if on_text:
                        on_text(text)
                for call in delta.get("tool_calls", []) or []:
                    index = int(call.get("index", 0))
                    current = tool_calls.setdefault(
                        index,
                        {
                            "id": call.get("id", ""),
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        },
                    )
                    if call.get("id"):
                        current["id"] = call["id"]
                    function = call.get("function", {})
                    current["function"]["name"] += str(function.get("name", ""))
                    current["function"]["arguments"] += str(
                        function.get("arguments", "")
                    )
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise AIRequestError(
            f"AI service returned HTTP {exc.code}: {details}"
        ) from exc
    except urllib.error.URLError as exc:
        raise AIRequestError(
            f"Cannot reach the AI service: {exc.reason}"
        ) from exc
    return {
        "id": response_id,
        "choices": [
            {
                "message": {
                    "content": "".join(content_parts),
                    "tool_calls": [
                        tool_calls[index] for index in sorted(tool_calls)
                    ],
                }
            }
        ],
        "usage": usage,
    }


def check_provider_health(settings: AISettings) -> dict[str, Any]:
    if settings.provider == "harness_sdk":
        return {"ok": settings.configured, "message": "Installed Harness SDK and provider selected; a conversation verifies the service.",
                "models": [settings.model], "latency_ms": 0}
    if not settings.configured:
        return {
            "ok": False,
            "message": "Provider, endpoint, model, or API key is missing.",
        }
    url = _endpoint(settings.base_url, "models")
    started = time.perf_counter()
    try:
        _validate_endpoint(
            url,
            allow_insecure_private_network=(
                settings.allow_insecure_private_network
            ),
        )
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {settings.request_api_key}",
                "User-Agent": f"{PRODUCT_NAME}/{PRODUCT_VERSION}",
            },
        )
        with urllib.request.urlopen(
            request,
            timeout=min(max(5, int(settings.timeout_seconds)), 30),
            context=ssl.create_default_context(),
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {
            "ok": False,
            "message": redact_sensitive_text(str(exc)),
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    models = [
        str(item.get("id"))
        for item in payload.get("data", [])
        if item.get("id")
    ]
    return {
        "ok": True,
        "message": "Provider is reachable.",
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "models": models[:50],
    }


def _extract_responses_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    fragments: list[str] = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    fragments.append(text)
    if fragments:
        return "\n".join(fragments)
    raise AIRequestError("The Responses API returned no assistant text.")


def _extract_chat_text(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIRequestError("The Chat API returned no assistant message.") from exc
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "")
            for item in content
            if item.get("type") in {"text", "output_text"}
        )
    raise AIRequestError("The Chat API returned an unsupported message format.")


def _extract_chat_tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        calls = payload["choices"][0]["message"].get("tool_calls", [])
    except (KeyError, IndexError, TypeError):
        return []
    normalized: list[dict[str, Any]] = []
    for call in calls or []:
        function = call.get("function", {})
        name = str(function.get("name", "")).strip()
        raw_arguments = function.get("arguments", "{}")
        try:
            arguments = (
                json.loads(raw_arguments)
                if isinstance(raw_arguments, str)
                else dict(raw_arguments)
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            arguments = {}
        if name:
            normalized.append(
                {
                    "id": str(call.get("id", "")),
                    "name": name,
                    "arguments": arguments,
                    "reason": "Requested by the configured model provider.",
                }
            )
    return normalized


def _parse_structured_text(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIRequestError(
            "The model response did not match NeuroEphys AI's JSON format."
        ) from exc
    if not isinstance(value, dict):
        raise AIRequestError("The model response must be a JSON object.")
    return value


def _parse_conversation_text(text: str) -> dict[str, Any]:
    """Accept prose from compatible providers without interpreting it as actions."""
    if not text.strip():
        return {}
    try:
        return _parse_structured_text(text)
    except AIRequestError:
        if text.lstrip().startswith(("{", "[", "```json")):
            raise
        return {"answer": text.strip()}


def normalize_ai_response(
    value: dict[str, Any],
    *,
    settings: AISettings,
    response_id: str = "",
    usage: dict[str, Any] | None = None,
    native_tool_calls: list[dict[str, Any]] | None = None,
    sent_field_categories: list[str] | None = None,
) -> AIResponse:
    warnings = [str(item) for item in value.get("warnings", [])][:12]
    plan: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value.get("plan", []):
        if not isinstance(item, dict):
            continue
        stage = str(item.get("stage", ""))
        if stage not in WORKFLOW_STAGES or stage in seen:
            continue
        seen.add(stage)
        parameters = []
        for parameter in item.get("recommended_parameters", [])[:20]:
            if not isinstance(parameter, dict):
                continue
            parameters.append(
                {
                    "name": str(parameter.get("name", "")),
                    "value": str(parameter.get("value", "")),
                    "rationale": str(parameter.get("rationale", "")),
                }
            )
        plan.append(
            {
                "stage": stage,
                "reason": str(item.get("reason", "")),
                "prerequisites": [
                    str(entry) for entry in item.get("prerequisites", [])[:12]
                ],
                "recommended_parameters": parameters,
            }
        )
    next_stage = str(value.get("suggested_next_stage", "import"))
    if next_stage not in WORKFLOW_STAGES:
        next_stage = plan[0]["stage"] if plan else "import"
    answer = str(value.get("answer") or "").strip()
    if not answer:
        # Managed OpenAI-compatible harnesses sometimes preserve the requested
        # JSON format but choose descriptive field names of their own. Recover a
        # readable advisory answer without treating any unregistered action as a
        # tool call. The original structured value remains remote text only.
        readiness = value.get("readiness_assessment")
        if isinstance(readiness, dict):
            answer = str(
                readiness.get("summary")
                or readiness.get("message")
                or readiness.get("status")
                or ""
            ).strip()
        if not answer:
            for key in (
                "summary",
                "message",
                "explanation",
                "response",
                "conclusion",
            ):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    answer = candidate.strip()
                    break
    tool_calls: list[dict[str, Any]] = []
    structured_tool_calls = value.get("tool_calls", [])
    if not isinstance(structured_tool_calls, list):
        structured_tool_calls = []
    # Some OpenAI-compatible managed harnesses return a constrained tool proposal
    # as {"tool": "name", "arguments": {...}, "reason": "..."} instead of the
    # native tool_calls envelope. Treat it as a proposal only; registry validation
    # and the local confirmation dialog still remain mandatory.
    if isinstance(value.get("tool"), str):
        structured_tool_calls = [
            *structured_tool_calls,
            {
                "name": value.get("tool"),
                "arguments": value.get("arguments", {}),
                "reason": value.get("reason", ""),
            },
        ]
    for proposal_key in ("proposed_tool_call", "tool_call"):
        proposal = value.get(proposal_key)
        if not isinstance(proposal, dict):
            continue
        structured_tool_calls = [
            *structured_tool_calls,
            {
                "name": proposal.get("tool") or proposal.get("name"),
                "arguments": proposal.get("arguments", {}),
                "reason": proposal.get("reason")
                or proposal.get("rationale", ""),
            },
        ]
    for item in [*structured_tool_calls, *(native_tool_calls or [])]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        arguments = item.get("arguments", {})
        if name not in TOOL_REGISTRY or not isinstance(arguments, dict):
            continue
        tool_calls.append(
            {
                "id": str(item.get("id", "")),
                "name": name,
                "arguments": arguments,
                "reason": str(item.get("reason", "")),
            }
        )
    if tool_calls and settings.ai_mode != AIMode.COLLABORATIVE:
        warnings.append(
            "The model proposed a tool call outside collaborative mode; "
            "NeuroEphys AI blocked it."
        )
        tool_calls = []
    if not answer and tool_calls:
        answer = (
            "A registered local action has been proposed. Review its inputs, "
            "validation result and confirmation dialog before execution."
        )
    if not answer:
        raise AIRequestError("The model returned an empty answer.")
    interpretation = value.get("scientific_interpretation") or {}
    if not isinstance(interpretation, dict):
        interpretation = {}
    normalized_interpretation = {
        key: [str(entry) for entry in interpretation.get(key, [])[:20]]
        for key in (
            "observed_results",
            "statistical_evidence",
            "possible_interpretations",
            "unsupported_conclusions",
            "limitations",
            "suggested_validation",
        )
    }
    return AIResponse(
        answer=answer,
        warnings=warnings,
        plan=plan,
        suggested_next_stage=next_stage,
        requires_user_confirmation=bool(
            value.get("requires_user_confirmation", True)
        ),
        model=settings.model,
        provider=settings.provider,
        response_id=response_id,
        usage=usage or {},
        tool_calls=tool_calls,
        scientific_interpretation=normalized_interpretation,
        sent_field_categories=list(sent_field_categories or []),
    )


def request_ai_advice(
    settings: AISettings,
    *,
    question: str,
    task: str,
    language: str,
    project_summary: dict[str, Any],
    history: list[dict[str, str]] | None = None,
    on_stream_text: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    project_queries=None,
    image_png: bytes | None = None,
) -> AIResponse:
    if image_png is not None:
        if not supports_image_input(settings.provider):
            raise AIConfigurationError(
                "Chart input is available for Harness SDK, institute/private "
                "OpenAI-compatible Chat, and OpenAI Responses connections. "
                "Select a vision-capable model."
            )
        if not image_png.startswith(b"\x89PNG\r\n\x1a\n") or len(image_png) > 6_000_000:
            raise ValueError("Chart attachment must be a valid PNG smaller than 6 MB.")
    if not settings.configured:
        raise AIConfigurationError(
            "Configure an endpoint, model, and API key before using cloud AI."
        )
    cloud_context = select_cloud_context(
        project_summary,
        settings.selected_context_fields,
    )
    sent_fields = sorted(cloud_context)
    instructions = build_system_instructions(
        language,
        task,
        settings.ai_mode,
    )
    instructions += (
        "\nA chart PNG is attached to this request. Describe only what is visibly "
        "supported, distinguish visual impressions from exact project metrics, "
        "and acknowledge unreadable labels or uncertain trends."
        if image_png is not None else
        "\nNo chart pixels are attached. Do not claim to have visually inspected a figure."
    )
    user_input = build_user_input(question, cloud_context, history)
    image_data_url = (
        "data:image/png;base64," + base64.b64encode(image_png).decode("ascii")
        if image_png is not None and settings.provider != "harness_sdk" else None
    )

    if settings.provider == "harness_sdk":
        from .harness_sdk import request_harness_sdk
        from .ai_project_bridge import ProjectMCPBridge, ProjectQueries
        queries = project_queries or ProjectQueries(None, project_summary.get("current_stage", "import"), settings.mode)
        queries.summary = cloud_context
        if settings.selected_context_fields and "queryable_data" not in settings.selected_context_fields:
            queries.allowed_sections = set()
        sdk_response_style = build_response_style_contract(language)
        sdk_instructions = (
            "You are NeuroEphys AI's research collaborator. Answer naturally in "
            + ("Simplified Chinese" if language == "zh_CN" else "English")
            + ". Discuss the user's actual question, not a mandatory workflow checklist. "
            "Use NeuroEphys MCP tools to inspect actual current data or results whenever details are needed. "
            "Tools read an immutable snapshot captured for this request; cite returned Q evidence IDs and snapshot time. "
            "For NeuroEphys AI operation instructions, search the versioned in-app tutorial with search_app_guidance before giving concrete steps. "
            "Use list_project_data to discover sections, nested paths and action schemas. Query pages rather than guessing. "
            "Earlier conversation is searchable within this project. Distinguish historical answers from current results. "
            "Answer general research, app-operation and other questions as well; do not force unrelated questions into the project workflow. "
            "Distinguish general model knowledge from verified project evidence and do not fabricate citations or current facts. "
            "Missing data is unknown, not zero. Ground truth is not ordinary sorting output. "
            "For multi-session studies preserve trial-to-session-to-animal hierarchy; equal Unit IDs are not matched cells, and session-held-out is not cross-animal validation. "
            "Supervised LDA and descriptive latent dynamics are different analyses. "
            "Only propose_analysis_action can propose app changes; it never executes them. "
            "Explain pending proposals as awaiting confirmation, never as completed. "
            "Do not propose actions when the user only asks for interpretation. "
            "Never invent measurements. Claim visual inspection only if a PNG image block is attached to this request; otherwise chart context describes labels and ranges, not pixels. "
            "When a chart is attached, identify visible trends and uncertainty, distinguish visual estimates from actual numeric results, and say when labels are unreadable. "
            "Write plain conversational text, not JSON. Apply the following response contract to every new answer:\n"
            + sdk_response_style
            + "\nMention evidence reads and proposed actions only as a short status. Preserve uncertainty and important warnings. "
            "Never expose private chain-of-thought; provide concise evidence and rationale instead.\n\n"
        )
        with ProjectMCPBridge(queries) as bridge:
            text = request_harness_sdk(provider=settings.harness_provider, model=settings.model,
                prompt=sdk_instructions + user_input, timeout=settings.timeout_seconds,
                cancel_event=cancel_event, on_text=on_stream_text, bridge=bridge,
                image_png=image_png)
        response = normalize_ai_response({"answer": text, "tool_calls": queries.proposals,
            "requires_user_confirmation": bool(queries.proposals)}, settings=settings,
            sent_field_categories=sent_fields)
        response.query_evidence = list(queries.audit)
        return response

    if settings.provider == "openai_responses":
        url = _endpoint(settings.base_url, "responses")
        payload: dict[str, Any] = {
            "model": settings.model,
            "instructions": instructions,
            "input": [{"role": "user", "content": (
                [{"type": "input_text", "text": user_input},
                 {"type": "input_image", "image_url": image_data_url}]
                if image_data_url else user_input
            )}],
            "store": False,
            "reasoning": {"effort": settings.reasoning_effort},
            "text": {
                "verbosity": "medium",
                "format": {
                    "type": "json_schema",
                    "name": "neuroflow_advice",
                    "strict": True,
                    "schema": AI_RESPONSE_SCHEMA,
                },
            },
        }
        if settings.safety_identifier:
            payload["safety_identifier"] = settings.safety_identifier
        raw = _post_json(
            url,
            payload,
            settings.request_api_key,
            settings.timeout_seconds,
            settings.retry_count,
            allow_insecure_private_network=(
                settings.allow_insecure_private_network
            ),
        )
        text = _extract_responses_text(raw)
        return normalize_ai_response(
            _parse_structured_text(text),
            settings=settings,
            response_id=str(raw.get("id", "")),
            usage=raw.get("usage", {}),
            sent_field_categories=sent_fields,
        )

    profile = PROVIDER_PROFILES.get(settings.provider, {})
    if profile.get("api_style") == "chat":
        url = _endpoint(settings.base_url, "chat/completions")
        payload = {
            "model": settings.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": (
                    [{"type": "text", "text": user_input},
                     {"type": "image_url", "image_url": {"url": image_data_url}}]
                    if image_data_url else user_input
                )},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        if image_data_url and settings.provider in {"openai_compatible", "private_compatible", "institute_harness"}:
            # Compatible gateways vary in structured-output support for vision.
            # The response parser accepts prose as well as JSON; do not reject an
            # otherwise valid image request just to force response_format.
            payload.pop("response_format")
        if settings.provider == "deepseek":
            thinking_enabled = settings.reasoning_effort != "none"
            payload["thinking"] = {
                "type": "enabled" if thinking_enabled else "disabled"
            }
            if thinking_enabled:
                payload["reasoning_effort"] = (
                    "max"
                    if settings.reasoning_effort in {"xhigh", "max"}
                    else "high"
                )
        elif settings.provider == "ollama":
            payload["reasoning_effort"] = settings.reasoning_effort
        if settings.ai_mode == AIMode.COLLABORATIVE:
            payload["tools"] = provider_tools()
            payload["tool_choice"] = "auto"
        if settings.stream and on_stream_text is not None:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
            raw = _post_chat_stream(
                url,
                payload,
                settings.request_api_key,
                settings.timeout_seconds,
                on_text=on_stream_text,
                cancel_event=cancel_event,
                allow_insecure_private_network=(
                    settings.allow_insecure_private_network
                ),
            )
        else:
            raw = _post_json(
                url,
                payload,
                settings.request_api_key,
                settings.timeout_seconds,
                settings.retry_count,
                allow_insecure_private_network=(
                    settings.allow_insecure_private_network
                ),
            )
        native_tool_calls = _extract_chat_tool_calls(raw)
        try:
            text = _extract_chat_text(raw)
        except AIRequestError:
            if not native_tool_calls:
                raise
            text = json.dumps(
                {
                    "answer": "",
                    "warnings": [],
                    "plan": [],
                    "suggested_next_stage": "import",
                    "requires_user_confirmation": True,
                }
            )
        parsed = _parse_conversation_text(text)
        proposals = native_tool_calls or parsed.get("tool_calls", [])
        read_names = {"inspect_project", "summarize_recording"}
        read_only = isinstance(proposals, list) and proposals and all(
            isinstance(call, dict) and call.get("name") in read_names
            for call in proposals
        )
        if read_only:
            payload["stream"] = False
            payload.pop("stream_options", None)
            payload.pop("tools", None)
            payload.pop("tool_choice", None)
            payload["messages"].append({"role": "user", "content":
                "Read-only project inspection result: " + json.dumps(cloud_context, ensure_ascii=False)
                + "\nUse this result to answer the original question now. Return a nonempty answer; no further tool calls."})
            raw = _post_json(url, payload, settings.request_api_key,
                settings.timeout_seconds, settings.retry_count,
                allow_insecure_private_network=settings.allow_insecure_private_network)
            parsed = _parse_conversation_text(_extract_chat_text(raw))
            native_tool_calls = []
        return normalize_ai_response(
            parsed,
            settings=settings,
            response_id=str(raw.get("id", "")),
            usage=raw.get("usage", {}),
            native_tool_calls=native_tool_calls,
            sent_field_categories=sent_fields,
        )

    raise AIConfigurationError(f"Unsupported AI provider: {settings.provider}")
