from __future__ import annotations

import textwrap
from typing import List, Tuple

TRANSLATION_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an expert in formal logic. Convert natural-language sentences into
    precise first-order logic (FOL) expressions using standard syntax: forall,
    exists, ->, &, |, not, parentheses, and predicate names starting with
    uppercase letters. Keep quantifiers explicit and prefer simple predicate
    names based on the nouns/verbs in the sentence.
    Respond ONLY with JSON that matches the requested schema.
    Use only json, no need to format the strings inside it.
    """
).strip()

ENTAILMENT_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an expert logician. Given natural-language premises and a conclusion,
    determine whether the conclusion is True, False, or Unknown (cannot be
    proven) with respect to the premises. Provide a short justification.
    Respond ONLY with JSON.
    """
).strip()


def build_translation_prompt(premises: List[str], conclusion: str) -> Tuple[str, str]:
    lines = ["Convert the following sentences into FOL:"]
    for idx, premise in enumerate(premises, 1):
        lines.append(f"Premise {idx}: {premise.strip()}")
    lines.append(f"Conclusion: {conclusion.strip()}")
    lines.append('Return JSON: {"premises_fol": ["..."], "conclusion_fol": "..."}')
    return "\n".join(lines), TRANSLATION_SYSTEM_PROMPT


def build_entailment_prompt(
    premises: List[str],
    conclusion: str,
) -> Tuple[str, str]:
    lines = ["Determine whether the conclusion follows from the premises:"]
    for idx, premise in enumerate(premises, 1):
        lines.append(f"Premise {idx}: {premise.strip()}")
    lines.append(f"Conclusion: {conclusion.strip()}")
    lines.append('Return JSON: {"label": "True|False|Unknown", "justification": "..."}')
    return "\n".join(lines), ENTAILMENT_SYSTEM_PROMPT
