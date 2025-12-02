from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class BenchmarkExample:
    """Normalized representation of a dataset example."""

    story_id: Optional[str]
    example_id: Optional[str]
    premises_nl: List[str]
    conclusion_nl: str
    premises_fol: Optional[List[str]] = None
    conclusion_fol: Optional[str] = None
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def sentences(self) -> Iterable[Dict[str, Any]]:
        """Iterate over all NL sentences with type metadata."""
        for idx, text in enumerate(self.premises_nl):
            yield {
                "type": "premise",
                "index": idx,
                "text": text.strip(),
            }
        yield {
            "type": "conclusion",
            "index": 0,
            "text": self.conclusion_nl.strip(),
        }
