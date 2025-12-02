from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from ..types import BenchmarkExample
from .base import DatasetLoader


class FolioDataset(DatasetLoader):
    """Loader for the FOLIO v0.0 dataset already vendored in the repo."""

    name = "folio"
    description = "FOLIO: Natural Language Reasoning with First-Order Logic"
    available_splits = {"train", "validation"}

    def __init__(self, root: Path | None = None, version: str = "v0.0") -> None:
        super().__init__(root=root)
        self.version = version
        self.data_dir = self.root / "datasets" / "FOLIO" / "data" / version
        if not self.data_dir.exists():
            raise FileNotFoundError(
                f"FOLIO data directory not found at {self.data_dir}."
            )
        self.split_map = {
            "train": self.data_dir / "folio-train.jsonl",
            "validation": self.data_dir / "folio-validation.jsonl",
        }

    def iter_examples(self, split: str) -> Iterable[BenchmarkExample]:
        split = self.validate_split(split)
        path = self.split_map[split]
        if not path.exists():
            raise FileNotFoundError(f"Split file not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                premises_nl: List[str] = record.get("premises", [])
                conclusion_nl: str = record.get("conclusion", "")
                premises_fol: Optional[List[str]] = record.get("premises-FOL")
                conclusion_fol: Optional[str] = record.get("conclusion-FOL")
                yield BenchmarkExample(
                    story_id=str(record.get("story_id")),
                    example_id=str(record.get("example_id")),
                    premises_nl=premises_nl,
                    conclusion_nl=conclusion_nl,
                    premises_fol=premises_fol,
                    conclusion_fol=conclusion_fol,
                    label=record.get("label"),
                    metadata={
                        "source": record.get("source"),
                        "raw": record,
                    },
                )
