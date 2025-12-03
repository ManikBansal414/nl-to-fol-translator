from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

from ..types import BenchmarkExample
from .backoff import call_with_backoff
from .cache import ResponseCache
from .prompts import build_sentence_translation_prompt, build_translation_prompt
from .registry import create_client


OPEN_FENCE_RE = re.compile(r"^```[^\n]*\r?\n")
CLOSE_FENCE_RE = re.compile(r"\r?\n?```$")


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    stripped = OPEN_FENCE_RE.sub("", stripped, count=1)
    stripped = CLOSE_FENCE_RE.sub("", stripped, count=1)
    return stripped.strip()


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

    clean_text = _strip_code_fences(text)
    try:
        parsed = json.loads(clean_text)
    except json.JSONDecodeError:
        parsed = {
            "premises_fol": None,
            "conclusion_fol": None,
            "error": f"Failed to parse JSON response: {clean_text[:120]}...",
        }
    return {
        "story_id": example.story_id,
        "example_id": example.example_id,
        "model": model_spec,
        "premises_fol": parsed.get("premises_fol"),
        "conclusion_fol": parsed.get("conclusion_fol"),
        "raw_text": clean_text,
        "raw_text_original": text,
        "raw_response": raw,
        "error": parsed.get("error"),
    }


def run_llm_sentence_translation(
    sentence: str,
    model_spec: str,
    cache: Optional[ResponseCache] = None,
) -> Dict[str, object]:
    client = create_client(model_spec)
    prompt, system_prompt = build_sentence_translation_prompt(sentence)

    payload = {
        "provider_model": model_spec,
        "mode": "translation_sentence",
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

    clean_text = _strip_code_fences(text)
    translation = None
    error = None
    try:
        parsed = json.loads(clean_text)
        translation = parsed.get("fol")
        error = parsed.get("error")
        if not translation and not error:
            error = "LLM response missing 'fol' field"
    except json.JSONDecodeError:
        error = f"Failed to parse JSON response: {clean_text[:120]}..."

    return {
        "model": model_spec,
        "translation": translation,
        "error": error,
        "raw_text": clean_text,
        "raw_text_original": text,
        "raw_response": raw,
    }
