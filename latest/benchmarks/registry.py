from __future__ import annotations

from typing import Dict, Iterable, Type

from .datasets import FolioDataset
from .datasets.base import DatasetLoader

_DATASETS: Dict[str, Type[DatasetLoader]] = {
    "folio": FolioDataset,
}


def get_dataset_names() -> Iterable[str]:
    return sorted(_DATASETS.keys())


def get_dataset_loader(name: str, **kwargs) -> DatasetLoader:
    try:
        dataset_cls = _DATASETS[name.lower()]
    except KeyError as exc:
        raise KeyError(
            f"Unknown dataset '{name}'. Available: {', '.join(get_dataset_names())}"
        ) from exc
    return dataset_cls(**kwargs)
