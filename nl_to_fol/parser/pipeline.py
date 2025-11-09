"""End-to-end translation pipeline.

Exposes:
- translate_sentence(text): normalize → NLP → match → render → validate

Helpers:
- _translate_simple: one-clause translation via matcher.
- _extract_implications: parse top-level "if ... then ..." pairs.
- _split_and: split top-level conjunctions of simple clauses.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from parser.config import DEBUG
from parser.data_structures import CapturedValue
from parser.fol_validator import validate_fol
from parser.matcher import match_rules
from parser.nlp import process
from parser.templates import TemplateResult, apply_template


def normalize_text(text: str) -> str:
    lowered = text.lower()
    filtered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    compact = re.sub(r"\s+", " ", filtered)
    return compact.strip()


def translate_sentence(sentence: str) -> str:
    normalized = normalize_text(sentence)
    if not normalized:
        return "[ERROR] Input sentence is empty."

    implications, rest = _extract_implications(normalized)
    fol_parts: List[str] = []

    for ante, cons in implications:
        a = _translate_simple(ante)
        if a.startswith("[ERROR]"):
            return a
        b = _translate_simple(cons)
        if b.startswith("[ERROR]"):
            return b
        fol_parts.append(f"({a} -> {b})")

    remaining = [seg for seg in _split_and(rest) if seg]
    for seg in remaining:
        s = _translate_simple(seg)
        if s.startswith("[ERROR]"):
            return s
        fol_parts.append(s)

    if not fol_parts:
        # No top-level IF-THEN found; treat whole sentence as simple.
        return _translate_simple(normalized)

    combined = " & ".join(fol_parts)
    if not validate_fol(combined):
        return f"[ERROR] Invalid FOL expression: {combined}"
    return combined


def _translate_simple(text: str) -> str:
    doc = process(text)
    match = match_rules(doc)
    if match is None:
        return "[ERROR] No rule matched."
    rule, slots = match
    template_result = apply_template(rule.template, slots)
    fol_expression = template_result.formatted
    if not validate_fol(fol_expression):
        return f"[ERROR] Invalid FOL expression: {fol_expression}"
    if DEBUG:
        _debug_print(rule.name, slots, template_result)
    return fol_expression


def _extract_implications(text: str) -> Tuple[List[Tuple[str, str]], str]:
    s = f" {text} "
    pairs: List[Tuple[str, str]] = []
    idx = 0
    while True:
        i = s.find(" if ", idx)
        if i == -1:
            break
        i += 1  # skip leading space
        then_pos = s.find(" then ", i + 3)
        if then_pos == -1:
            break
        ante = s[i + 3:then_pos].strip()
        # Consequent ends at next ' and if ' or end
        next_and_if = s.find(" and if ", then_pos + 6)
        if next_and_if == -1:
            cons = s[then_pos + 6:].strip()
            s = s[:i]  # remove processed tail
            pairs.append((ante, cons))
            break
        else:
            cons = s[then_pos + 6:next_and_if].strip()
            pairs.append((ante, cons))
            idx = next_and_if + 1
    rest = s.strip()
    return pairs, rest


def _split_and(text: str) -> List[str]:
    if not text:
        return []
    parts = [p.strip() for p in text.split(" and ")]
    return [p for p in parts if p]


def _debug_print(rule_name: str, slots: Dict[str, CapturedValue], result: TemplateResult) -> None:
    print(f"[DEBUG] Matched rule: {rule_name}")
    print("[DEBUG] Extracted slots:")
    seen = set()
    for key, capture in sorted(slots.items()):
        if key != capture.placeholder or key in seen:
            continue
        tokens = " ".join(token.text for token in capture.tokens)
        print(f"    {key}: {tokens}")
        seen.add(key)
    print(f"[DEBUG] Intermediate template: {result.raw}")
    print(f"[DEBUG] Final FOL: {result.formatted}")
