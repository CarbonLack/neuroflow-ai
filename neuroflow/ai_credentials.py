from __future__ import annotations

import os

from .product import PRODUCT_NAME

_SERVICE_NAME = f"{PRODUCT_NAME} model providers"
_SESSION_KEYS: dict[str, str] = {}


def provider_environment_variable(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized == "deepseek":
        return "DEEPSEEK_API_KEY"
    if normalized == "openai_responses":
        return "OPENAI_API_KEY"
    return "NEUROEPHYS_AI_API_KEY"


def get_api_key(provider: str) -> str:
    provider = provider.strip().lower()
    environment = os.environ.get(provider_environment_variable(provider), "")
    if environment:
        return environment.strip()
    if provider in _SESSION_KEYS:
        return _SESSION_KEYS[provider]
    try:
        import keyring

        return (keyring.get_password(_SERVICE_NAME, provider) or "").strip()
    except Exception:
        return ""


def store_api_key(
    provider: str,
    api_key: str,
    *,
    persist_in_os_store: bool,
) -> None:
    provider = provider.strip().lower()
    value = api_key.strip()
    if not value:
        delete_api_key(provider)
        return
    _SESSION_KEYS[provider] = value
    if not persist_in_os_store:
        return
    try:
        import keyring

        keyring.set_password(_SERVICE_NAME, provider, value)
    except Exception as exc:
        raise RuntimeError(
            "The operating-system credential store is unavailable. "
            "The key remains available for this running session only."
        ) from exc


def delete_api_key(provider: str) -> None:
    provider = provider.strip().lower()
    _SESSION_KEYS.pop(provider, None)
    try:
        import keyring

        keyring.delete_password(_SERVICE_NAME, provider)
    except Exception:
        pass
