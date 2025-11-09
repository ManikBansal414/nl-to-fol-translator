"""FOL syntax validator using a small Lark grammar.

Exposes:
- validate_fol(text): returns True if parseable by the grammar.
"""
from lark import Lark

# Tiny FOL grammar
grammar = r"""
?start: expr

?expr: impl
?impl: or_expr ("->" impl)?
?or_expr: and_expr ("|" and_expr)*
?and_expr: unary ("&" unary)*
?unary: quant
     | "not" unary
     | predicate
     | "(" expr ")"

quant: ("forall" | "exists") VAR "." expr

predicate: NAME "(" [args] ")"
args: term ("," term)*

?term: VAR | NAME

VAR: /[a-z][a-z0-9_]*/
NAME: /[A-Z][A-Za-z0-9_]*/

%import common.WS
%ignore WS
"""

parser = Lark(grammar, start="start", parser="lalr")

def validate_fol(text):
    try:
        parser.parse(text)
        return True
    except:
        return False
