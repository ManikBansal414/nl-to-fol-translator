from __future__ import annotations
from typing import List
import re
from lark import Lark, Transformer, v_args
from .ast_nodes import (
    TruthValue, Predicate, Identity, Function, Not, And, Or, Implies, Bicond, Universal, Existential
)

grammar = r"""
?start: expr
?expr: iff
?iff: implies (("<->"|"<=>"|"↔") implies)?            -> bicond_op
?implies: or_expr (("->"|"=>"|"→") implies)?          -> implies_op
?or_expr: and_expr (("|"|"∨") and_expr)*               -> or_op
?and_expr: unary (("&"|"∧") unary)*                    -> and_op
?unary: quant
    | ("not"|"!"|"~"|"¬") unary                   -> neg
    | equality
    | predicate
    | "(" expr ")"

quant: (("forall"|"exists")|("∀"|"∃")) varlist "." expr
varlist: VAR ("," VAR)*

equality: term (("="|"!="|"≠") term)                 -> eq_op

predicate: NAME "(" [terms] ")"
terms: term ("," term)*
?term: VAR                -> var
    | NAME               -> const
    | NAME "(" [terms] ")" -> func

VAR: /[a-z][a-z0-9_]*/
NAME: /[A-Z][A-Za-z0-9_]*/

%import common.WS
%ignore WS
"""

@v_args(inline=True)
class ASTBuilder(Transformer):
    def var(self, name):
        return str(name)
    def const(self, name):
        return str(name)
    def func(self, name, *args):
        terms = []
        for a in args:
            if isinstance(a, list):
                terms.extend(a)
            else:
                terms.append(a)
        return Function(str(name), terms)
    def terms(self, *items):
        out = []
        for it in items:
            if isinstance(it, list):
                out.extend(it)
            else:
                out.append(it)
        return out
    def predicate(self, name, terms=None):
        return Predicate(str(name), ([] if terms is None else terms))
    def eq_op(self, left, op, right):
        op_str = str(op)
        node = Identity(left, right)
        if op_str in ('!=', '≠'):
            return Not(node)
        return node
    def neg(self, f):
        return Not(f)
    def and_op(self, first, *rest):
        node = first
        for r in rest:
            node = And(node, r)
        return node
    def or_op(self, first, *rest):
        node = first
        for r in rest:
            node = Or(node, r)
        return node
    def implies_op(self, left, right=None):
        if right is None:
            return left
        return Implies(left, right)
    def bicond_op(self, left, right=None):
        if right is None:
            return left
        return Bicond(left, right)
    def quant(self, qtok, vars_list, dot, expr):
        q = str(qtok)
        # vars_list is a list of str vars
        vars_flat = vars_list if isinstance(vars_list, list) else [vars_list]
        node = expr
        for v in reversed(vars_flat):
            if q in ('forall', '∀'):
                node = Universal(str(v), node)
            else:
                node = Existential(str(v), node)
        return node

_parser = Lark(grammar, start='start', parser='lalr')

def tokenize(s: str):
    # Provided for API compatibility; returns original string.
    return s

def _strip_outer_parens(s: str) -> str:
    s = s.strip()
    if not s or s[0] != '(' or s[-1] != ')':
        return s
    depth = 0
    for i, ch in enumerate(s):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0 and i != len(s) - 1:
                return s
    if depth == 0:
        return s[1:-1].strip()
    return s


def parse(tokens_or_str):
    s = tokens_or_str if isinstance(tokens_or_str, str) else ''.join(tokens_or_str)
    try:
        # Normalize by stripping redundant outer parentheses
        prev = None
        while s != prev:
            prev = s
            s = _strip_outer_parens(s)
        # Handle top-level implication/bicond with quantified RHS manually
        def _find_top_level(hay: str, needle: str) -> int:
            depth = 0
            i = 0
            L = len(hay)
            nL = len(needle)
            while i <= L - nL:
                ch = hay[i]
                if ch == '(':
                    depth += 1
                    i += 1
                    continue
                if ch == ')':
                    depth -= 1
                    i += 1
                    continue
                if depth == 0 and hay.startswith(needle, i):
                    return i
                i += 1
            return -1

        idx = _find_top_level(s, '->')
        if idx == -1:
            idx = _find_top_level(s, '→')
        if idx != -1:
            left = s[:idx].strip()
            right = s[idx+2:].strip() if s[idx:idx+2] in ('->', '→') else s[idx+1:].strip()
            if re.match(r'^(forall|exists|∀|∃)\b', right):
                lnode = parse(left)
                rnode = parse(right)
                if lnode is not None and rnode is not None:
                    return Implies(lnode, rnode)
        idx2 = _find_top_level(s, '<->')
        if idx2 == -1:
            idx2 = _find_top_level(s, '↔')
        if idx2 != -1:
            left = s[:idx2].strip()
            right = s[idx2+3:].strip()
            if re.match(r'^(forall|exists|∀|∃)\b', right):
                lnode = parse(left)
                rnode = parse(right)
                if lnode is not None and rnode is not None:
                    return Bicond(lnode, rnode)
        m = re.match(r"^(forall|exists)\s+([a-z][a-z0-9_]*)\s*\.\s*(.+)$", s)
        if m:
            q, var, rest = m.group(1), m.group(2), m.group(3)
            sub = parse(rest)
            if sub is None:
                return None
            return Universal(var, sub) if q == 'forall' else Existential(var, sub)
        tree = _parser.parse(s)
        return ASTBuilder().transform(tree)
    except Exception:
        return None

def atomicTok(tok: str) -> bool:
    # Returns True if token string looks like an atomic predicate or identity
    return bool(tok) and (tok[0].isupper() or tok.startswith('=('))
