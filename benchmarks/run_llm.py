from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from tqdm import tqdm

from .llm.cache import ResponseCache
from .llm.entailment import run_llm_entailment
from .llm.translators import run_llm_translation
from .metrics import aggregate_entailment_rows, aggregate_translation_rows
from .registry import get_dataset_loader


def write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_summary(path: Path, summary: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)


def run(
    dataset: str,
    split: str,
    mode: str,
    model_spec: str,
    limit: int | None,
    use_cache: bool,
    show_progress: bool,
) -> List[Dict[str, object]]:
    loader = get_dataset_loader(dataset)
    cache = ResponseCache() if use_cache else None
    rows: List[Dict[str, object]] = []
    total = limit if limit is not None else None
    progress: Optional[tqdm] = None
    if show_progress:
        progress = tqdm(total=total, unit="example", desc="LLM", leave=False)
    try:
        for idx, example in enumerate(loader.iter_examples(split)):
            if limit is not None and idx >= limit:
                break
            if mode == "translation":
                result = run_llm_translation(
                    example, model_spec=model_spec, cache=cache
                )
            else:
                result = run_llm_entailment(example, model_spec=model_spec, cache=cache)
                result["label"] = example.label
            rows.append(result)
            if progress is not None:
                progress.update(1)
    finally:
        if progress is not None:
            progress.close()
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM baselines for NL→FOL tasks.")
    parser.add_argument("--dataset", default="folio", help="Dataset name")
    parser.add_argument("--split", default="validation", help="Dataset split")
    parser.add_argument(
        "--mode", choices=["translation", "entailment"], default="translation"
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model spec in form provider:model (e.g., openai:gpt-4o-mini)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Optional cap on examples"
    )
    parser.add_argument(
        "--cache", action="store_true", help="Enable on-disk cache for responses"
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=None,
        help="Path to write per-example outputs",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Path to write aggregate summary",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress output (enabled by default for interactive terminals)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    show_progress = (not args.no_progress) and sys.stderr.isatty()
    rows = run(
        dataset=args.dataset,
        split=args.split,
        mode=args.mode,
        model_spec=args.model,
        limit=args.limit,
        use_cache=args.cache,
        show_progress=show_progress,
    )

    if args.mode == "translation":
        summary = aggregate_translation_rows(rows)
    else:
        summary = aggregate_entailment_rows(rows)

    print(f"Dataset: {args.dataset} | Split: {args.split} | Mode: {args.mode}")
    if args.mode == "translation":
        print(f"Examples: {summary['total_sentences']}")
        print(
            f"Translations: {summary['translations']} ({summary['translation_rate']:.2%})"
        )
    else:
        print(f"Examples: {summary['total_examples']}")
        print(f"Predictions: {summary['predictions']}")
        print(f"Accuracy: {summary['accuracy']:.2%}")
    if args.output_jsonl:
        write_jsonl(args.output_jsonl, rows)
        print(f"Wrote outputs to {args.output_jsonl}")
    if args.summary_json:
        write_summary(args.summary_json, summary)
        print(f"Wrote summary to {args.summary_json}")


if __name__ == "__main__":
    main()
