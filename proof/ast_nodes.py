from __future__ import annotations
from dataclasses import dataclass
from typing import List, Union

Term = Union[str, 'Function']

@dataclass(frozen=True)
class TruthValue:
    value: bool
    def __str__(self) -> str:
        return 'T' if self.value else 'F'

@dataclass(frozen=True)
class Predicate:
    name: str
    terms: List[Term]
    def __str__(self) -> str:
        inner = ','.join(str(t) for t in self.terms)
        return f"{self.name}({inner})"

@dataclass(frozen=True)
class Identity:
    left: Term
    right: Term
    def __str__(self) -> str:
        return f"=({self.left},{self.right})"

@dataclass(frozen=True)
class Function:
    name: str
    terms: List[Term]
    def __str__(self) -> str:
        inner = ','.join(str(t) for t in self.terms)
        return f"{self.name}({inner})"

@dataclass(frozen=True)
class Not:
    formula: object
    def __str__(self) -> str:
        return f"not {self.formula}" if not isinstance(self.formula, (And, Or, Implies, Bicond)) else f"not ({self.formula})"

@dataclass(frozen=True)
class And:
    left: object
    right: object
    def __str__(self) -> str:
        return f"({self.left} & {self.right})"

@dataclass(frozen=True)
class Or:
    left: object
    right: object
    def __str__(self) -> str:
        return f"({self.left} | {self.right})"

@dataclass(frozen=True)
class Implies:
    left: object
    right: object
    def __str__(self) -> str:
        return f"({self.left} -> {self.right})"

@dataclass(frozen=True)
class Bicond:
    left: object
    right: object
    def __str__(self) -> str:
        return f"({self.left} <-> {self.right})"

@dataclass(frozen=True)
class Universal:
    var: str
    formula: object
    def __str__(self) -> str:
        return f"forall {self.var}. {self.formula}"

@dataclass(frozen=True)
class Existential:
    var: str
    formula: object
    def __str__(self) -> str:
        return f"exists {self.var}. {self.formula}"
