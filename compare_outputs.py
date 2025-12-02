from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from benchmarks.metrics import (
    aggregate_entailment_rows,
    aggregate_translation_rows,
)


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path: Path) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_summary(path: Path, mode: str) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _read_json(path)
    if suffix == ".jsonl":
        rows = _read_jsonl(path)
        if mode == "translation":
            return aggregate_translation_rows(rows)
        return aggregate_entailment_rows(rows)
    raise ValueError(f"Unsupported file extension for {path}")


def _flatten(metrics: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    for key, value in metrics.items():
        dotted = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, dotted))
        else:
            flat[dotted] = value
    return flat


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _format_delta(a: Any, b: Any) -> str:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        delta = b - a
        return f"{delta:+.6f}"
    return "-"


def compare_outputs(args: argparse.Namespace) -> None:
    first = _load_summary(args.first, args.mode)
    second = _load_summary(args.second, args.mode)
    flat_first = _flatten(first)
    flat_second = _flatten(second)

    keys = sorted(set(flat_first) | set(flat_second))
    first_label = args.first_label or args.first.stem
    second_label = args.second_label or args.second.stem

    header = f"{'Metric':40} {first_label:>20} {second_label:>20} {'Delta (second-first)':>23}"
    print(header)
    print("-" * len(header))
    for key in keys:
        a = flat_first.get(key)
        b = flat_second.get(key)
        print(
            f"{key:40} {_format_value(a):>20} {_format_value(b):>20} {_format_delta(a, b):>23}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two benchmark outputs (rows JSONL or summary JSON) and "
            "print metric deltas."
        )
    )
    parser.add_argument("first", type=Path, help="Path to baseline summary/rows file")
    parser.add_argument(
        "second", type=Path, help="Path to comparison summary/rows file"
    )
    parser.add_argument(
        "--mode",
        choices=["translation", "entailment"],
        default="translation",
        help="Specify which aggregation logic to apply when JSONL inputs are provided.",
    )
    parser.add_argument(
        "--first-label",
        default=None,
        help="Optional label for the first file in the report",
    )
    parser.add_argument(
        "--second-label",
        default=None,
        help="Optional label for the second file in the report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    compare_outputs(args)


if __name__ == "__main__":
    main()
