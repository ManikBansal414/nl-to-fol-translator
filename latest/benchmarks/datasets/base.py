from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Set

from ..types import BenchmarkExample


class DatasetLoader(ABC):
    """Abstract interface for benchmark datasets."""

    name: str
    description: str
    available_splits: Set[str]

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2]

    @abstractmethod
    def iter_examples(self, split: str) -> Iterable[BenchmarkExample]:
        """Yield normalized examples for the requested split."""
        raise NotImplementedError

    def validate_split(self, split: str) -> str:
        if split not in self.available_splits:
            raise ValueError(
                f"Split '{split}' not available for dataset '{self.name}'. "
                f"Options: {sorted(self.available_splits)}"
            )
        return split
