"""Template expansion and FOL formatting.

Exposes:
- apply_template(template, slots) -> TemplateResult
- pretty_print_fol(expr): whitespace and punctuation normalization

Key types:
- TemplateResult: holds raw and pretty-printed strings.
- TemplateRenderer: replaces placeholders (/NOUN, /VERB, /VAR) deterministically.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from parser.data_structures import CapturedValue


@dataclass
class TemplateResult:
    raw: str
    formatted: str


class VariableGenerator:
    _sequence = ["x", "y", "z"]

    def __init__(self) -> None:
        self.generated: List[str] = []

    def next(self) -> str:
        idx = len(self.generated)
        if idx < len(self._sequence):
            name = self._sequence[idx]
        else:
            base = self._sequence[idx % len(self._sequence)]
            suffix = idx // len(self._sequence)
            name = f"{base}{suffix}"
        self.generated.append(name)
        return name


class TemplateRenderer:
    def __init__(self, template: str, slots: Dict[str, CapturedValue]) -> None:
        self.template = template
        self.slots = slots
        self.var_gen = VariableGenerator()

    def render(self) -> str:
        step = self._replace_vars(self.template)
        step = self._replace_predicate_calls(step)
        step = self._replace_constants(step)
        return step

    def _replace_vars(self, text: str) -> str:
        result: List[str] = []
        idx = 0
        pending_quantifier: Optional[str] = None
        var_stack: List[str] = []
        length = len(text)

        while idx < length:
            if text.startswith("forall", idx):
                result.append("forall")
                idx += 6
                pending_quantifier = "forall"
                continue
            if text.startswith("exists", idx):
                result.append("exists")
                idx += 6
                pending_quantifier = "exists"
                continue
            if text.startswith("/VAR", idx):
                if pending_quantifier is not None or not var_stack:
                    var_name = self.var_gen.next()
                    var_stack.append(var_name)
                else:
                    var_name = var_stack[-1]
                result.append(var_name)
                idx += 4
                pending_quantifier = None
                continue

            char = text[idx]
            result.append(char)
            if not char.isspace():
                pending_quantifier = None
            idx += 1

        return ''.join(result)

    def _replace_predicate_calls(self, text: str) -> str:
        pattern = re.compile(r"/([A-Z]+(?:_[0-9]+)?)\(([^()]*)\)")
        while True:
            match = pattern.search(text)
            if not match:
                break
            placeholder = f"/{match.group(1)}"
            args = match.group(2).strip()
            replacement = self._render_predicate_call(placeholder, args)
            text = text[:match.start()] + replacement + text[match.end():]
        return text

    def _render_predicate_call(self, placeholder: str, args: str) -> str:
        capture = self._lookup_capture(placeholder)
        if capture is None:
            name = self._format_symbol(placeholder.lstrip('/'))
            return f"{name}({args})"

        names = self._predicate_names(capture)
        calls = [f"{name}({args})" for name in names]
        if len(calls) > 1:
            return "(" + " & ".join(calls) + ")"
        return calls[0]

    def _replace_constants(self, text: str) -> str:
        pattern = re.compile(r"/([A-Z]+(?:_[0-9]+)?)")

        def repl(match: re.Match[str]) -> str:
            placeholder = f"/{match.group(1)}"
            capture = self._lookup_capture(placeholder)
            if capture is None:
                return self._format_symbol(match.group(1))
            return self._format_constant(capture)

        return pattern.sub(repl, text)

    def _lookup_capture(self, placeholder: str) -> Optional[CapturedValue]:
        return self.slots.get(placeholder)

    def _predicate_names(self, capture: CapturedValue) -> List[str]:
        names: List[str] = []
        base = (capture.base_type or '').upper()
        for token in capture.tokens:
            if base == "PROPN":
                names.append(self._format_proper(token.text))
            elif base == "VERB":
                names.append(self._format_symbol(token.lemma))
            else:
                names.append(self._format_symbol(token.lemma))
        return names

    def _format_constant(self, capture: CapturedValue) -> str:
        base = (capture.base_type or '').upper()
        parts: List[str] = []
        for token in capture.tokens:
            if base == "PROPN":
                parts.append(self._format_proper(token.text))
            else:
                parts.append(self._format_symbol(token.lemma))
        return "_".join(parts)

    def _format_symbol(self, text: str) -> str:
        cleaned = re.sub(r"[^a-z0-9 ]", " ", text.lower())
        parts = [part for part in cleaned.split() if part]
        if not parts:
            return "Entity"
        return ''.join(part.capitalize() for part in parts)

    def _format_proper(self, text: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9]", " ", text)
        parts = [part for part in cleaned.split() if part]
        if not parts:
            return "Name"
        return ''.join(part.capitalize() for part in parts)


def apply_template(template: str, slots: Dict[str, CapturedValue]) -> TemplateResult:
    renderer = TemplateRenderer(template, slots)
    raw_expression = renderer.render()
    formatted_expression = pretty_print_fol(raw_expression)
    return TemplateResult(raw=raw_expression, formatted=formatted_expression)


def pretty_print_fol(expr: str) -> str:
    text = expr.strip()
    replacements = {
        "->": " -> ",
        "&": " & ",
        "|": " | ",
        "=": " = ",
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\( ", "(", text)
    text = re.sub(r" \)", ")", text)
    text = re.sub(r",\s+", ", ", text)
    text = re.sub(r"\.\s+", ". ", text)
    return text.strip()
