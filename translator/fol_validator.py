"""FOL syntax validator using a small Lark grammar (common)."""
from lark import Lark, Tree

grammar = r"""
?start: expr
?expr: iff
?iff: implies (("<->" | "<=>" | "↔") implies)?
?implies: or_expr (("->" | "=>" | "→") implies)?
?or_expr: and_expr (("|" | "∨") and_expr)*
?and_expr: unary (("&" | "∧") unary)*
?unary: quant | ("not" | "!" | "~" | "¬") unary | equality | predicate | "(" expr ")"
quant: (("forall" | "exists") | ("∀" | "∃")) varlist "." expr
varlist: VAR ( ("," VAR) | VAR )*
equality: term ("=" | "!=" | "≠") term
predicate: NAME "(" [terms] ")"
terms: term ("," term)*
?term: VAR | NAME | NAME "(" [terms] ")"
VAR: /[a-z][a-z0-9_]*/
NAME: /[A-Z][A-Za-z0-9_]*/
%import common.WS
%ignore WS
"""

_parser = Lark(grammar, start="start", parser="lalr")

def validate_fol(text: str) -> bool:
    try:
        _parser.parse(text)
        return True
    except Exception:
        return False


def parse_fol(text: str) -> Tree:
    """Parse FOL text and return the Lark parse tree (raises on failure)."""
    return _parser.parse(text)
