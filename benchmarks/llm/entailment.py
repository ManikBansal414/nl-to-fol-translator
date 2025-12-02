from __future__ import annotations

import json
from typing import Dict, Optional

from ..types import BenchmarkExample
from .backoff import call_with_backoff
from .cache import ResponseCache
from .prompts import build_entailment_prompt
from .registry import create_client


VALID_LABELS = {"true", "false", "unknown"}


def run_llm_entailment(
    example: BenchmarkExample,
    model_spec: str,
    cache: Optional[ResponseCache] = None,
) -> Dict[str, object]:
    client = create_client(model_spec)
    prompt, system_prompt = build_entailment_prompt(
        example.premises_nl, example.conclusion_nl
    )
    payload = {
        "provider_model": model_spec,
        "mode": "entailment",
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

    label = None
    justification = None
    error = None
    try:
        parsed = json.loads(text)
        label_candidate = str(parsed.get("label", "")).strip().lower()
        if label_candidate in VALID_LABELS:
            label = label_candidate.capitalize()
        else:
            error = f"Invalid label '{parsed.get('label')}'"
        justification = parsed.get("justification")
    except json.JSONDecodeError:
        error = f"Failed to parse JSON response: {text[:120]}..."

    return {
        "story_id": example.story_id,
        "example_id": example.example_id,
        "model": model_spec,
        "predicted_label": label,
        "justification": justification,
        "raw_text": text,
        "raw_response": raw,
        "error": error,
    }
