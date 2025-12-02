"""Core lightweight data structures used by matcher and templates (common)."""
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TokenData:
    text: str
    lemma: str
    pos: str
    dep: str
    index: int

    @classmethod
    def from_spacy(cls, token):
        return cls(
            text=token.text,
            lemma=token.lemma_.lower(),
            pos=token.pos_,
            dep=token.dep_,
            index=token.i,
        )


@dataclass
class CapturedValue:
    placeholder: str
    base_type: str
    tokens: List[TokenData]

    def __post_init__(self):
        if not isinstance(self.tokens, list):
            self.tokens = list(self.tokens)

    @property
    def multi(self) -> bool:
        return len(self.tokens) > 1

    @property
    def signature(self) -> tuple:
        return tuple(t.index for t in self.tokens)

    def lemmas(self) -> List[str]:
        return [t.lemma for t in self.tokens]

    def texts(self) -> List[str]:
        return [t.text for t in self.tokens]

    def pos_tags(self) -> List[str]:
        return [t.pos for t in self.tokens]

    def __eq__(self, other) -> bool:
        if not isinstance(other, CapturedValue):
            return False
        return self.base_type == other.base_type and self.signature == other.signature

    def __hash__(self) -> int:
        return hash((self.base_type, self.signature))
