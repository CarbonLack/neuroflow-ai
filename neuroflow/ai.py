from __future__ import annotations

import json
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
    "private_compatible": {
        "label": "Laboratory/private compatible service",
        "base_url": "https://model-server.example/v1",
        "models": [],
        "api_style": "chat",
    },
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
    api_key: str = field(
        default_factory=lambda: get_api_key("deepseek"),
        repr=False,
    )

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip() and self.base_url.strip() and self.model.strip())

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
        "context_schema": "neuroephys.cloud-project-summary.v1",
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
        "regression_summary": _compact_json_value(state.regression),
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


def build_system_instructions(
    language: str,
    task: str,
    mode: AIMode | str = AIMode.ASSISTANT,
) -> str:
    output_language = "Simplified Chinese" if language == "zh_CN" else "English"
    mode_value = str(mode)
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
13. Cite only sources present in the versioned local knowledge context. If no source
    is supplied, state that a source lookup is still required.
14. The current task type is {task!r}. Return the required JSON object with no
    markdown code fence.
""".strip()


def build_user_input(
    question: str,
    project_summary: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> str:
    safe_history = []
    for item in (history or [])[-6:]:
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


def _validate_endpoint(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}:
        return
    raise AIConfigurationError(
        "The AI endpoint must use HTTPS. Plain HTTP is allowed only for localhost."
    )


def _post_json(
    url: str,
    payload: dict[str, Any],
    api_key: str,
    timeout_seconds: int,
    retry_count: int = 0,
) -> dict[str, Any]:
    _validate_endpoint(url)
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
) -> dict[str, Any]:
    _validate_endpoint(url)
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
    if not settings.configured:
        return {
            "ok": False,
            "message": "Provider, endpoint, model, or API key is missing.",
        }
    url = _endpoint(settings.base_url, "models")
    _validate_endpoint(url)
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {settings.api_key.strip()}",
            "User-Agent": f"{PRODUCT_NAME}/{PRODUCT_VERSION}",
        },
    )
    started = time.perf_counter()
    try:
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
    answer = str(value.get("answer", "")).strip()
    tool_calls: list[dict[str, Any]] = []
    for item in [*value.get("tool_calls", []), *(native_tool_calls or [])]:
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
    interpretation = value.get("scientific_interpretation", {})
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
) -> AIResponse:
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
    user_input = build_user_input(question, cloud_context, history)

    if settings.provider == "openai_responses":
        url = _endpoint(settings.base_url, "responses")
        payload: dict[str, Any] = {
            "model": settings.model,
            "instructions": instructions,
            "input": [{"role": "user", "content": user_input}],
            "store": False,
            "reasoning": {"effort": settings.reasoning_effort},
            "text": {
                "verbosity": "high",
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
            settings.api_key.strip(),
            settings.timeout_seconds,
            settings.retry_count,
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
                {"role": "user", "content": user_input},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        if settings.ai_mode == AIMode.COLLABORATIVE:
            payload["tools"] = provider_tools()
            payload["tool_choice"] = "auto"
        if settings.stream and on_stream_text is not None:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
            raw = _post_chat_stream(
                url,
                payload,
                settings.api_key.strip(),
                settings.timeout_seconds,
                on_text=on_stream_text,
                cancel_event=cancel_event,
            )
        else:
            raw = _post_json(
                url,
                payload,
                settings.api_key.strip(),
                settings.timeout_seconds,
                settings.retry_count,
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
        return normalize_ai_response(
            _parse_structured_text(text),
            settings=settings,
            response_id=str(raw.get("id", "")),
            usage=raw.get("usage", {}),
            native_tool_calls=native_tool_calls,
            sent_field_categories=sent_fields,
        )

    raise AIConfigurationError(f"Unsupported AI provider: {settings.provider}")
