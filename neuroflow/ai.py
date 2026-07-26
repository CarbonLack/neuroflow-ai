from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .models import ProjectState

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


@dataclass(slots=True)
class AISettings:
    provider: str = "openai_responses"
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-5.6-terra"
    reasoning_effort: str = "medium"
    timeout_seconds: int = 90
    include_recent_log: bool = False
    safety_identifier: str = ""
    api_key: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""),
        repr=False,
    )

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip() and self.base_url.strip() and self.model.strip())

    @property
    def provider_label(self) -> str:
        return (
            "OpenAI Responses API"
            if self.provider == "openai_responses"
            else "OpenAI-compatible Chat API"
        )


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
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def audit_record(self, question: str, task: str) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "task": task,
            "question": question,
            "answer": self.answer,
            "warnings": self.warnings,
            "plan": self.plan,
            "suggested_next_stage": self.suggested_next_stage,
            "requires_user_confirmation": self.requires_user_confirmation,
            "provider": self.provider,
            "model": self.model,
            "response_id": self.response_id,
            "usage": self.usage,
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

    sorting_units = {
        sorter: len(spikes_by_unit)
        for sorter, spikes_by_unit in state.sorting_results.items()
    }
    summary: dict[str, Any] = {
        "project_open": True,
        "source_type": state.source_type,
        "electrode_type": state.electrode_type,
        "sampling_rate_hz": state.sampling_rate,
        "channel_count": state.channel_count,
        "duration_seconds": state.duration_seconds,
        "dtype": state.dtype,
        "event_count": len(state.events),
        "trial_count": len(state.trials),
        "sorting_results": sorting_units,
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
        "analysis_summary": _compact_json_value(state.analysis),
        "statistics_summary": _compact_json_value(state.statistics),
        "decoding_summary": _compact_json_value(state.decoding),
        "regression_summary": _compact_json_value(state.regression),
        "allowed_stages": list(WORKFLOW_STAGES),
    }
    if include_recent_log:
        summary["recent_log"] = [
            redact_sensitive_text(item) for item in state.run_log[-5:]
        ]
    return summary


_WINDOWS_PATH = re.compile(r"(?i)\b[A-Z]:\\(?:[^\\\r\n]+\\)*[^\\\r\n]*")
_UNIX_PATH = re.compile(r"(?<!\w)/(?:[^/\s]+/)+[^/\s]*")
_API_KEY = re.compile(r"\b(?:sk|sess)-[A-Za-z0-9_-]{12,}\b")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def redact_sensitive_text(text: str) -> str:
    redacted = _WINDOWS_PATH.sub("<local-path-redacted>", str(text))
    redacted = _UNIX_PATH.sub("<local-path-redacted>", redacted)
    redacted = _API_KEY.sub("<api-key-redacted>", redacted)
    return _EMAIL.sub("<email-redacted>", redacted)


def build_system_instructions(language: str, task: str) -> str:
    output_language = "Simplified Chinese" if language == "zh_CN" else "English"
    return f"""
You are NeuroFlow's advisory electrophysiology assistant. Reply in {output_language}.

Your role is to explain, review, diagnose, and propose a candidate workflow. Numerical
calculation is performed by NeuroFlow's deterministic local modules, not by you.

Hard boundaries:
1. Never claim that a step ran, a unit is biologically valid, or a scientific
   hypothesis is proven unless the supplied project summary contains that evidence.
2. Never invent a channel, event, unit, effect size, p-value, model score, file, or
   software result.
3. Keep raw QC, preprocessing, spike sorting, Unit QC, synchronization, statistics,
   and interpretation distinct. State missing prerequisites explicitly.
4. A proposed plan may use only these stage keys:
   {", ".join(WORKFLOW_STAGES)}.
5. AI advice is optional. Important parameters, costly sorting, result replacement,
   and scientific interpretation require user review and confirmation.
6. Do not request raw voltage or personally identifying metadata. Work only from the
   path-free structured summary.
7. Distinguish a default starting point from a universally correct parameter. Explain
   why a recommendation fits the supplied recording and what the user must inspect.
8. The current task type is {task!r}. Return the required JSON object and no markdown
   code fence.
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
) -> dict[str, Any]:
    _validate_endpoint(url)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "NeuroFlow/0.8",
        },
    )
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
        raise AIRequestError(f"AI service returned HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise AIRequestError(f"Cannot reach the AI service: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AIRequestError("The AI request timed out.") from exc
    except json.JSONDecodeError as exc:
        raise AIRequestError("The AI service returned invalid JSON.") from exc


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


def _parse_structured_text(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIRequestError("The model response did not match NeuroFlow's JSON format.") from exc
    if not isinstance(value, dict):
        raise AIRequestError("The model response must be a JSON object.")
    return value


def normalize_ai_response(
    value: dict[str, Any],
    *,
    settings: AISettings,
    response_id: str = "",
    usage: dict[str, Any] | None = None,
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
    if not answer:
        raise AIRequestError("The model returned an empty answer.")
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
    )


def request_ai_advice(
    settings: AISettings,
    *,
    question: str,
    task: str,
    language: str,
    project_summary: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> AIResponse:
    if not settings.configured:
        raise AIConfigurationError(
            "Configure an endpoint, model, and API key before using cloud AI."
        )
    instructions = build_system_instructions(language, task)
    user_input = build_user_input(question, project_summary, history)

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
        )
        text = _extract_responses_text(raw)
        return normalize_ai_response(
            _parse_structured_text(text),
            settings=settings,
            response_id=str(raw.get("id", "")),
            usage=raw.get("usage", {}),
        )

    if settings.provider == "openai_compatible":
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
        raw = _post_json(
            url,
            payload,
            settings.api_key.strip(),
            settings.timeout_seconds,
        )
        text = _extract_chat_text(raw)
        return normalize_ai_response(
            _parse_structured_text(text),
            settings=settings,
            response_id=str(raw.get("id", "")),
            usage=raw.get("usage", {}),
        )

    raise AIConfigurationError(f"Unsupported AI provider: {settings.provider}")
