from __future__ import annotations

from typing import Optional

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from .base import LLMClient, LLMResponse


class GeminiClient(LLMClient):
    provider = "gemini"
    env_var = "GOOGLE_API_KEY"
    retriable_exceptions = (ResourceExhausted,)

    def _init_client(self) -> None:
        genai.configure(api_key=self.api_key)
        self._client = genai.GenerativeModel(self.model)

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        final_prompt = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
        response = self._client.generate_content(
            final_prompt,
            generation_config={"temperature": temperature},
        )
        text = (response.text or "").strip()
        return LLMResponse(text=text, raw=response.to_dict())
