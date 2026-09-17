from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


@dataclass(frozen=True, slots=True)
class HarnessProfile:
    """Non-secret connection metadata discovered from a supported harness."""

    provider_id: str
    display_name: str
    base_url: str
    api_style: str
    models: tuple[str, ...]
    default_model: str
    api_key_env: str
    source: str


def deepseek_harness_settings_path() -> Path:
    return Path.home() / ".dsh" / "settings.yaml"


def _safe_url(value: Any) -> str:
    url = str(value or "").strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    if parsed.username or parsed.password:
        return ""
    return url


def discover_deepseek_harness_profiles(
    settings_path: Path | None = None,
) -> list[HarnessProfile]:
    """Read public provider metadata without reading harness credentials.

    DeepSeek Harness stores provider endpoints and model identifiers in
    ``~/.dsh/settings.yaml``. Secrets live in a separate credential store and are
    deliberately not opened here.
    """

    path = settings_path or deepseek_harness_settings_path()
    if not path.is_file():
        return []
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError):
        return []
    if not isinstance(payload, dict):
        return []
    provider_root = payload.get("llm-pi-ai", {})
    providers = (
        provider_root.get("providers", {})
        if isinstance(provider_root, dict)
        else {}
    )
    if not isinstance(providers, dict):
        return []
    default_root = payload.get("agent-default-model", {})
    default_provider = (
        str(default_root.get("provider", ""))
        if isinstance(default_root, dict)
        else ""
    )
    configured_default_model = (
        str(default_root.get("model", ""))
        if isinstance(default_root, dict)
        else ""
    )
    discovered: list[HarnessProfile] = []
    for provider_id, raw in providers.items():
        if not isinstance(raw, dict):
            continue
        api_style = str(raw.get("api", "")).strip()
        if api_style not in {"openai-completions", "openai-chat"}:
            continue
        base_url = _safe_url(raw.get("baseURL"))
        if not base_url:
            continue
        models: list[str] = []
        for item in raw.get("models", []) or []:
            model_id = (
                str(item.get("id", "")).strip()
                if isinstance(item, dict)
                else str(item).strip()
            )
            if model_id and model_id not in models:
                models.append(model_id)
        default_model = (
            configured_default_model
            if str(provider_id) == default_provider
            and configured_default_model in models
            else (models[0] if models else configured_default_model)
        )
        discovered.append(
            HarnessProfile(
                provider_id=str(provider_id),
                display_name=str(raw.get("displayName") or provider_id),
                base_url=base_url,
                api_style=api_style,
                models=tuple(models),
                default_model=default_model,
                api_key_env=str(raw.get("apiKeyEnv", "")).strip(),
                source="DeepSeek Harness settings",
            )
        )
    discovered.sort(
        key=lambda item: (item.provider_id != default_provider, item.display_name)
    )
    return discovered
