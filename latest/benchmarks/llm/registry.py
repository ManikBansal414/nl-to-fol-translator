from __future__ import annotations

from typing import Dict, Iterable

from .base import LLMClient
from .env import load_env_files
from .gemini_client import GeminiClient
from .openai_client import OpenAIClient

_CLIENTS: Dict[str, type[LLMClient]] = {
    "openai": OpenAIClient,
    "gemini": GeminiClient,
}


def list_models() -> Iterable[str]:
    return [
        "openai:gpt-4o-mini",
        "openai:gpt-4.1-mini",
        "gemini:gemini-1.5-flash",
        "gemini:gemini-1.5-pro",
    ]


def create_client(model_spec: str) -> LLMClient:
    load_env_files()
    if ":" not in model_spec:
        raise ValueError(
            "Model spec must be 'provider:model', e.g., openai:gpt-4o-mini"
        )
    provider, model = model_spec.split(":", 1)
    provider = provider.lower()
    try:
        cls = _CLIENTS[provider]
    except KeyError as exc:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {', '.join(_CLIENTS)}"
        ) from exc
    return cls(model=model)
