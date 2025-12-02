from __future__ import annotations
import re
from typing import Dict, List, Tuple

from .fol_validator import validate_fol
from .matcher import match_rules
from .nlp import process
from .templates import apply_template, TemplateResult


def normalize_text(text: str) -> str:
    lowered = text.lower()
    filtered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    compact = re.sub(r"\s+", " ", filtered)
    return compact.strip()


def translate_sentence(sentence: str) -> str:
    raw = sentence.strip()
    normalized = normalize_text(sentence)
    if not normalized:
        return "[ERROR] Input sentence is empty."
    implications, rest = _extract_implications(normalized)
    fol_parts: List[str] = []
    for ante, cons in implications:
        a = _translate_simple(ante)
        if a.startswith('[ERROR]'):
            return a
        b = _translate_simple(cons)
        if b.startswith('[ERROR]'):
            return b
        fol_parts.append(f'({a} -> {b})')
    if not implications:
        # Use original-cased text to preserve PROPN tagging
        remaining = [seg for seg in _split_and_raw(raw) if seg]
    else:
        remaining = [seg for seg in _split_and(rest) if seg]
    for seg in remaining:
        s = _translate_simple(seg)
        if s.startswith('[ERROR]'):
            return s
        fol_parts.append(s)
    if not fol_parts:
        # Fall back to original-cased sentence to keep proper nouns
        return _translate_simple(raw)
    combined = ' & '.join(fol_parts)
    if not validate_fol(combined):
        return f"[ERROR] Invalid FOL expression: {combined}"
    return combined


def _translate_simple(text: str) -> str:
    doc = process(text)
    match = match_rules(doc)
    if match is None:
        return "[ERROR] No rule matched."
    rule, slots = match
    result: TemplateResult = apply_template(rule.template, slots)
    fol_expression = result.formatted
    if not validate_fol(fol_expression):
        return f"[ERROR] Invalid FOL expression: {fol_expression}"
    return fol_expression


def _extract_implications(text: str) -> Tuple[List[Tuple[str, str]], str]:
    s = f" {text} "
    pairs: List[Tuple[str, str]] = []
    idx = 0
    while True:
        i = s.find(" if ", idx)
        if i == -1:
            break
        i += 1
        then_pos = s.find(" then ", i + 3)
        if then_pos == -1:
            break
        ante = s[i + 3:then_pos].strip()
        next_and_if = s.find(" and if ", then_pos + 6)
        if next_and_if == -1:
            cons = s[then_pos + 6:].strip()
            s = s[:i]
            pairs.append((ante, cons))
            break
        else:
            cons = s[then_pos + 6:next_and_if].strip()
            pairs.append((ante, cons))
            idx = next_and_if + 1
    return pairs, s.strip()


def _split_and(text: str) -> List[str]:
    if not text:
        return []
    return [p.strip() for p in text.split(' and ') if p.strip()]

def _split_and_raw(text: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r"\s+and\s+", text, flags=re.I)
    return [p.strip() for p in parts if p.strip()]
