from __future__ import annotations

import json
from typing import Dict, List, Optional

from ..types import BenchmarkExample
from .backoff import call_with_backoff
from .cache import ResponseCache
from .prompts import build_translation_prompt
from .registry import create_client


def run_llm_translation(
    example: BenchmarkExample,
    model_spec: str,
    premises_subset: Optional[List[str]] = None,
    cache: Optional[ResponseCache] = None,
) -> Dict[str, object]:
    client = create_client(model_spec)
    premises = premises_subset if premises_subset is not None else example.premises_nl
    prompt, system_prompt = build_translation_prompt(premises, example.conclusion_nl)

    payload = {
        "provider_model": model_spec,
        "mode": "translation",
        "prompt": prompt,
        "system_prompt": system_prompt,
    }

    def _call_completion():
        response = client.complete(prompt, system_prompt=system_prompt)
        return {"text": response.text, "raw": response.raw}

    if cache:
        cached = cache.get(payload)
        if cached is not None:
            text = cached["text"]
            raw = cached.get("raw", {})
        else:
            result = call_with_backoff(
                _call_completion,
                retriable_exceptions=client.retriable_exceptions,
            )
            text = result["text"]
            raw = result["raw"]
            cache.set(payload, result)
    else:
        result = call_with_backoff(
            _call_completion,
            retriable_exceptions=client.retriable_exceptions,
        )
        text = result["text"]
        raw = result["raw"]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {
            "premises_fol": None,
            "conclusion_fol": None,
            "error": f"Failed to parse JSON response: {text[:120]}...",
        }
    return {
        "story_id": example.story_id,
        "example_id": example.example_id,
        "model": model_spec,
        "premises_fol": parsed.get("premises_fol"),
        "conclusion_fol": parsed.get("conclusion_fol"),
        "raw_text": text,
        "raw_response": raw,
        "error": parsed.get("error"),
    }
