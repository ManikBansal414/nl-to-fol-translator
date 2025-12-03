from __future__ import annotations

from typing import Optional

from openai import OpenAI, RateLimitError

from .base import LLMClient, LLMResponse


class OpenAIClient(LLMClient):
    provider = "openai"
    env_var = "OPENAI_API_KEY"
    retriable_exceptions = (RateLimitError,)

    def _init_client(self) -> None:
        self._client = OpenAI(api_key=self.api_key)

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        choice = response.choices[0].message
        text = choice.content or ""
        return LLMResponse(text=text.strip(), raw=response.model_dump())
