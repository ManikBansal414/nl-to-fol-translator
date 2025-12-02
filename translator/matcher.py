"""Rule loader and matcher (common)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import yaml

from .data_structures import CapturedValue, TokenData

RULE_PATH = Path(__file__).resolve().parent / "rules.yaml"

_CAPTURABLE = {"NOUN", "PROPN", "VERB", "ADJ", "ADV", "PRON"}
_VERB_POS = {"VERB", "AUX"}
_NOUN_POS = {"NOUN", "PROPN"}
_SUBJECT_DEPS = ("nsubj", "nsubjpass", "csubj")
_OBJECT_DEPS = ("obj", "dobj", "pobj", "dative")
_COMPLEMENT_DEPS = ("attr", "ccomp", "xcomp", "acomp")
_MODIFIER_DEPS = ("amod", "advmod")


@dataclass
class PatternElement:
    raw: str
    kind: str
    value: Optional[str] = None
    optional: bool = False
    multi: bool = False
    placeholder: Optional[str] = None
    base_type: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


@dataclass
class DependencySlot:
    role: str
    base_type: str
    placeholder: str
    deps: Tuple[str, ...]
    aliases: List[str] = field(default_factory=list)


@dataclass
class CompiledRule:
    name: str
    template: str
    pattern: List[PatternElement]
    dependency: List[DependencySlot]
    specificity: Tuple[int, int, int, int]


class PlaceholderRegistry:
    def __init__(self) -> None:
        self.counts: Dict[str, int] = defaultdict(int)
        self.primary_alias: Dict[str, str] = {}

    def assign(
        self, base_type: str, explicit: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        base = base_type.upper()
        aliases: List[str] = []

        if explicit:
            placeholder = explicit
            index = _placeholder_index(explicit) or 1
            self.counts[base] = max(self.counts[base], index)
            if base not in self.primary_alias and index == 1:
                aliases.append(f"/{base}")
                aliases.append(f"/{base}_1")
                self.primary_alias[base] = explicit
            elif index == 1:
                alias = f"/{base}"
                if alias != explicit:
                    aliases.append(alias)
                alias = f"/{base}_1"
                if alias != explicit:
                    aliases.append(alias)
            return placeholder, aliases

        self.counts[base] += 1
        index = self.counts[base]
        if index == 1:
            placeholder = f"/{base}"
            aliases.append(f"/{base}_1")
            self.primary_alias[base] = placeholder
        else:
            placeholder = f"/{base}_{index}"
        return placeholder, aliases


def load_rules(path: Path = RULE_PATH) -> List[CompiledRule]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        raw_rules = yaml.safe_load(handle) or []

    compiled: List[CompiledRule] = []
    for idx, raw in enumerate(raw_rules):
        if not isinstance(raw, dict):
            continue
        compiled.append(_compile_rule(raw, idx))

    compiled.sort(key=lambda r: r.specificity, reverse=True)
    return compiled


def match_rules(doc) -> Optional[Tuple[CompiledRule, Dict[str, CapturedValue]]]:
    tokens, token_lookup = _collect_tokens(doc)
    if not tokens:
        return None

    for rule in RULES:
        slots: Optional[Dict[str, CapturedValue]] = None

        if rule.dependency:
            slots = dependency_match(doc, rule, token_lookup)
        if slots is None:
            slots = try_match(tokens, rule.pattern)
        if slots is not None:
            return rule, slots

    return None


def dependency_match(
    doc, rule: CompiledRule, token_lookup: Dict[int, TokenData]
) -> Optional[Dict[str, CapturedValue]]:
    if not rule.dependency:
        return None

    verb_slots = [slot for slot in rule.dependency if slot.role == "verb"]
    if not verb_slots:
        return None

    for token in doc:
        token_data = token_lookup.get(token.i)
        if token_data is None:
            continue
        # Avoid generating generic Be(subject) from copula in the intransitive rule
        if rule.name == "dep-intransitive-verb" and token_data.lemma == "be":
            continue
        for verb_slot in verb_slots:
            if not _token_matches_base(token_data, verb_slot.base_type):
                continue
            base_slots: Dict[str, CapturedValue] = {}
            capture = CapturedValue(
                verb_slot.placeholder, verb_slot.base_type, [token_data]
            )
            updated_slots = _store_capture(base_slots, capture, verb_slot.aliases)
            if updated_slots is None:
                continue
            populated = _populate_dependency_roles(
                token, rule.dependency, updated_slots, token_lookup
            )
            if populated is not None:
                return populated
    return None


def _populate_dependency_roles(
    verb_token,
    slots: List[DependencySlot],
    current: Dict[str, CapturedValue],
    lookup: Dict[int, TokenData],
) -> Optional[Dict[str, CapturedValue]]:
    result = dict(current)
    for slot in slots:
        if slot.role == "verb":
            continue
        tokens = _find_dependency_tokens(verb_token, slot, lookup)
        if not tokens:
            return None
        capture = CapturedValue(slot.placeholder, slot.base_type, tokens)
        updated = _store_capture(result, capture, slot.aliases)
        if updated is None:
            return None
        result = updated
    return result


def try_match(
    tokens: Sequence[TokenData], pattern: Sequence[PatternElement]
) -> Optional[Dict[str, CapturedValue]]:
    def backtrack(
        token_idx: int, pattern_idx: int, slots: Dict[str, CapturedValue]
    ) -> Optional[Dict[str, CapturedValue]]:
        if pattern_idx == len(pattern):
            return slots if token_idx == len(tokens) else None

        element = pattern[pattern_idx]

        match_result = _attempt_element_match(
            tokens, token_idx, pattern_idx, slots, element, backtrack
        )
        if match_result is not None:
            return match_result

        if element.optional:
            return backtrack(token_idx, pattern_idx + 1, dict(slots))
        return None

    return backtrack(0, 0, {})


def _attempt_element_match(
    tokens: Sequence[TokenData],
    token_idx: int,
    pattern_idx: int,
    slots: Dict[str, CapturedValue],
    element: PatternElement,
    backtrack_fn,
) -> Optional[Dict[str, CapturedValue]]:
    if element.kind == "literal":
        if token_idx >= len(tokens):
            return None
        token = tokens[token_idx]
        if token.lemma != element.value and token.text.lower() != (element.value or ""):
            return None
        return backtrack_fn(token_idx + 1, pattern_idx + 1, slots)

    if element.kind == "wildcard":
        if token_idx >= len(tokens):
            return None
        return backtrack_fn(token_idx + 1, pattern_idx + 1, slots)

    if element.kind == "pos":
        if token_idx >= len(tokens):
            return None
        if not _token_matches_base(tokens[token_idx], element.base_type):
            return None
        return backtrack_fn(token_idx + 1, pattern_idx + 1, slots)

    if element.kind == "placeholder":
        matches = _collect_placeholder_matches(tokens, token_idx, element)
        for consumed, capture_tokens in matches:
            capture = CapturedValue(
                element.placeholder or element.raw,
                element.base_type or "",
                capture_tokens,
            )
            updated_slots = _store_capture(slots, capture, element.aliases)
            if updated_slots is None:
                continue
            result = backtrack_fn(token_idx + consumed, pattern_idx + 1, updated_slots)
            if result is not None:
                return result
    return None


def _collect_placeholder_matches(
    tokens: Sequence[TokenData],
    start: int,
    element: PatternElement,
) -> List[Tuple[int, List[TokenData]]]:
    results: List[Tuple[int, List[TokenData]]] = []
    if start >= len(tokens):
        return results

    def token_ok(candidate: TokenData) -> bool:
        return _token_matches_base(candidate, element.base_type)

    if not element.multi:
        token = tokens[start]
        if token_ok(token):
            results.append((1, [token]))
        return results

    span: List[TokenData] = []
    for idx in range(start, len(tokens)):
        token = tokens[idx]
        if not token_ok(token):
            break
        span.append(token)
    for length in range(len(span), 0, -1):
        results.append((length, span[:length]))
    return results


def _store_capture(
    slots: Dict[str, CapturedValue],
    capture: CapturedValue,
    aliases: Iterable[str],
) -> Optional[Dict[str, CapturedValue]]:
    placeholder = capture.placeholder
    if not placeholder:
        return dict(slots)
    result = dict(slots)
    for key in [placeholder, *aliases]:
        existing = result.get(key)
        if existing is not None and existing != capture:
            return None
        result[key] = capture
    return result


def _find_dependency_tokens(
    verb_token, slot: DependencySlot, lookup: Dict[int, TokenData]
) -> List[TokenData]:
    for child in verb_token.children:
        if child.dep_ not in slot.deps:
            continue
        token_data = lookup.get(child.i)
        if token_data is None:
            continue
        if _token_matches_base(token_data, slot.base_type):
            return [token_data]

    head = verb_token.head
    if head is not None and head != verb_token:
        for child in head.children:
            if child.dep_ not in slot.deps:
                continue
            token_data = lookup.get(child.i)
            if token_data is None:
                continue
            if _token_matches_base(token_data, slot.base_type):
                return [token_data]
    return []


def _token_matches_base(token: TokenData, base: Optional[str]) -> bool:
    if base is None:
        return False
    tag = base.upper()
    if tag == "NOUN":
        return token.pos in _NOUN_POS
    if tag == "VERB":
        return token.pos in _VERB_POS
    return token.pos == tag


def _collect_tokens(doc) -> Tuple[List[TokenData], Dict[int, TokenData]]:
    tokens: List[TokenData] = []
    lookup: Dict[int, TokenData] = {}
    for token in doc:
        if token.is_space or token.is_punct:
            continue
        data = TokenData.from_spacy(token)
        tokens.append(data)
        lookup[token.i] = data
    return tokens, lookup


def _compile_rule(rule: Dict, index: int) -> CompiledRule:
    name = rule.get("name") or f"rule_{index + 1}"
    template = rule.get("template", "")
    raw_pattern = rule.get("pattern", []) or []
    dependency_spec = rule.get("dependency") or {}

    registry = PlaceholderRegistry()
    pattern_elements = [_parse_pattern_token(token, registry) for token in raw_pattern]
    dependency_slots = _parse_dependency_spec(dependency_spec, registry)

    literal_count = sum(1 for element in pattern_elements if element.kind == "literal")
    placeholder_count = sum(
        1 for element in pattern_elements if element.kind == "placeholder"
    )
    optional_count = sum(1 for element in pattern_elements if element.optional)
    length = len(pattern_elements)
    specificity = (literal_count, placeholder_count, -optional_count, -length)

    return CompiledRule(
        name=name,
        template=template,
        pattern=pattern_elements,
        dependency=dependency_slots,
        specificity=specificity,
    )


def _parse_pattern_token(token: str, registry: PlaceholderRegistry) -> PatternElement:
    raw = str(token)
    optional = raw.endswith("?")
    if optional:
        raw = raw[:-1]
    multi = raw.endswith("+")
    if multi:
        raw = raw[:-1]

    if raw == "_":
        return PatternElement(
            raw=token, kind="wildcard", optional=optional, multi=multi
        )

    if raw.startswith("/"):
        base, explicit = _split_placeholder(raw)
        placeholder, aliases = registry.assign(base, explicit)
        return PatternElement(
            raw=token,
            kind="placeholder",
            placeholder=placeholder,
            base_type=base,
            optional=optional,
            multi=multi,
            aliases=aliases,
        )

    if raw.isupper():
        base_type = raw.upper()
        if base_type in _CAPTURABLE:
            placeholder, aliases = registry.assign(base_type)
            return PatternElement(
                raw=token,
                kind="placeholder",
                placeholder=placeholder,
                base_type=base_type,
                optional=optional,
                multi=multi,
                aliases=aliases,
            )
        return PatternElement(
            raw=token,
            kind="pos",
            base_type=base_type,
            optional=optional,
            multi=multi,
        )

    return PatternElement(
        raw=token,
        kind="literal",
        value=raw.lower(),
        optional=optional,
        multi=multi,
    )


def _parse_dependency_spec(
    spec: Dict, registry: PlaceholderRegistry
) -> List[DependencySlot]:
    if not isinstance(spec, dict):
        return []
    slots: List[DependencySlot] = []
    for role, descriptor in spec.items():
        base_type: Optional[str] = None
        placeholder: Optional[str] = None
        deps: Tuple[str, ...] = ()
        if isinstance(descriptor, dict):
            base_type = str(descriptor.get("pos", descriptor.get("type", ""))).upper()
            placeholder = descriptor.get("placeholder")
            dep_value = descriptor.get("dep")
            if isinstance(dep_value, str):
                deps = (dep_value,)
            elif isinstance(dep_value, Iterable):
                deps = tuple(str(d) for d in dep_value)
        else:
            base_type = str(descriptor).upper()

        if not base_type:
            continue

        deps = deps or _default_deps(role)
        placeholder_name, aliases = registry.assign(base_type, placeholder)
        slots.append(
            DependencySlot(
                role=str(role),
                base_type=base_type,
                placeholder=placeholder_name,
                deps=deps,
                aliases=aliases,
            )
        )
    return slots


def _split_placeholder(token: str) -> Tuple[str, Optional[str]]:
    core = token[1:]
    base = core
    if "_" in core:
        base = core.split("_", 1)[0]
    return base.upper(), token


def _placeholder_index(name: str) -> Optional[int]:
    if "_" not in name:
        return None
    try:
        return int(name.split("_")[-1])
    except ValueError:
        return None


def _default_deps(role: str) -> Tuple[str, ...]:
    lowered = role.lower()
    if lowered == "subject":
        return _SUBJECT_DEPS
    if lowered == "object":
        return _OBJECT_DEPS
    if lowered == "complement":
        return _COMPLEMENT_DEPS
    if lowered == "modifier":
        return _MODIFIER_DEPS
    return _OBJECT_DEPS


RULES: List[CompiledRule] = load_rules()
