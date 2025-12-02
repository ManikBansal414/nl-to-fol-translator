from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
from zss import Node, simple_distance
from lark import Tree, Token

from translator import parse_fol

VAR_RE = re.compile(r"^[a-z][a-z0-9_]*$")
NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_]*$")
TOKEN_PATTERN = re.compile(
    r"forall|exists|not|and|or|<->|<=>|↔|->|=>|→|==|!=|≠|=|\(|\)|,|\.|&|∧|\||∨|~|¬|!|[A-Za-z0-9_]+"
)
KEYWORDS = {"forall", "exists", "not", "and", "or"}


def tokenize_fol(text: str) -> List[str]:
    return [tok for tok in TOKEN_PATTERN.findall(text) if tok.strip()]


def canonicalize_fol(text: str) -> str:
    tokens = tokenize_fol(text)
    var_map: Dict[str, str] = {}
    next_id = 0
    result: List[str] = []
    for tok in tokens:
        lower = tok.lower()
        if VAR_RE.match(tok):
            if tok not in var_map:
                var_map[tok] = f"v{next_id}"
                next_id += 1
            result.append(var_map[tok])
        elif lower in KEYWORDS:
            result.append(lower)
        else:
            result.append(tok)
    return " ".join(result)


def _term_to_repr(node: Tree | Token) -> str:
    if isinstance(node, Token):
        return node.value
    if isinstance(node, Tree):
        if node.data == "terms":
            return ",".join(_term_to_repr(child) for child in node.children)
        if node.data == "term":
            if not node.children:
                return ""
            head = _term_to_repr(node.children[0])
            if len(node.children) == 1:
                return head
            args = _term_to_repr(node.children[1])
            return f"{head}({args})"
    return str(node)


def extract_predicates(text: str) -> Set[Tuple[str, Tuple[str, ...]]]:
    try:
        tree = parse_fol(text)
    except Exception:
        return set()
    predicates: Set[Tuple[str, Tuple[str, ...]]] = set()
    for subtree in tree.iter_subtrees():
        if isinstance(subtree, Tree) and getattr(subtree, "data", None) == "predicate":
            name_token = subtree.children[0]
            name = (
                name_token.value if isinstance(name_token, Token) else str(name_token)
            )
            args: List[str] = []
            if len(subtree.children) > 1:
                arg_node = subtree.children[1]
                if isinstance(arg_node, Tree) and arg_node.data == "terms":
                    for term in arg_node.children:
                        args.append(_term_to_repr(term))
            predicates.add((name, tuple(args)))
    return predicates


def predicate_metrics(predicted: str, gold: str) -> Tuple[float, float, float]:
    pred_set = extract_predicates(predicted)
    gold_set = extract_predicates(gold)
    if not pred_set and not gold_set:
        return 1.0, 1.0, 1.0
    if not pred_set:
        return 0.0, 0.0, 0.0
    tp = len(pred_set & gold_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def bleu_score(predicted: str, gold: str) -> float:
    pred_tokens = tokenize_fol(predicted)
    gold_tokens = tokenize_fol(gold)
    if not pred_tokens or not gold_tokens:
        return 0.0
    smoothie = SmoothingFunction().method1
    try:
        return float(
            sentence_bleu([gold_tokens], pred_tokens, smoothing_function=smoothie)
        )
    except ZeroDivisionError:
        return 0.0


def _tree_to_node(tree: Tree | Token) -> Node:
    if isinstance(tree, Token):
        label = f"{tree.type}:{tree.value}"
        return Node(label)
    label = tree.data if isinstance(tree.data, str) else str(tree.data)
    node = Node(label)
    for child in tree.children:
        node.addkid(_tree_to_node(child))
    return node


def _node_size(node: Node) -> int:
    return 1 + sum(_node_size(child) for child in node.children)


def tree_similarity(predicted: str, gold: str) -> Optional[float]:
    try:
        pred_tree = parse_fol(predicted)
        gold_tree = parse_fol(gold)
    except Exception:
        return None
    pred_node = _tree_to_node(pred_tree)
    gold_node = _tree_to_node(gold_tree)
    dist = simple_distance(pred_node, gold_node)
    denom = max(_node_size(pred_node), _node_size(gold_node))
    if denom == 0:
        return 1.0
    return 1.0 - (dist / denom)


def evaluate_parsing_pair(predicted: str, gold: str) -> Dict[str, float]:
    metrics: Dict[str, float] = {}
    canonical_pred = canonicalize_fol(predicted)
    canonical_gold = canonicalize_fol(gold)
    metrics["exact_match"] = 1.0 if canonical_pred == canonical_gold else 0.0
    precision, recall, f1 = predicate_metrics(predicted, gold)
    metrics["predicate_precision"] = precision
    metrics["predicate_recall"] = recall
    metrics["predicate_f1"] = f1
    metrics["bleu"] = bleu_score(predicted, gold)
    tree_sim = tree_similarity(predicted, gold)
    if tree_sim is not None:
        metrics["tree_similarity"] = tree_sim
    return metrics
