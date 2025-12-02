from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LLMResponse:
    text: str
    raw: Dict[str, Any]


class LLMClient:
    """Simple abstraction around provider-specific SDKs."""

    provider: str
    model: str
    retriable_exceptions: tuple[type[Exception], ...] = tuple()

    def __init__(self, model: str, api_key: Optional[str] = None) -> None:
        self.model = model
        self.api_key = api_key or self._env_api_key()
        if not self.api_key:
            raise RuntimeError(
                f"API key missing for provider '{self.provider}'. "
                "Set it via environment variable or pass api_key explicitly."
            )
        self._init_client()

    # Overridden in subclasses -------------------------------------------------

    env_var: str = ""

    def _env_api_key(self) -> Optional[str]:
        return os.getenv(self.env_var) if self.env_var else None

    def _init_client(self) -> None:  # pragma: no cover - to be implemented
        raise NotImplementedError

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:  # pragma: no cover - to be implemented
        raise NotImplementedError
