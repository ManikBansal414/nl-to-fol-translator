from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import logging

from tqdm import tqdm

from method_fomaster.validator import validate as validate_fomaster
from method_lark.validator import validate as validate_lark
from method_nltk.validator import validate as validate_nltk

from .fol_analysis import evaluate_parsing_pair
from .llm.cache import ResponseCache
from .llm.entailment import run_llm_entailment
from .llm.translators import run_llm_sentence_translation, run_llm_translation
from .metrics import aggregate_entailment_rows, aggregate_translation_rows
from .registry import get_dataset_loader
from .types import BenchmarkExample

VALIDATORS = {
    "lark": validate_lark,
    "nltk": validate_nltk,
    "fomaster": validate_fomaster,
}

LOGGER = logging.getLogger(__name__)


class JsonlCheckpointWriter:
    """Write rows to a JSONL file incrementally for crash-safe progress."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", encoding="utf-8")

    def write(self, row: Dict[str, object]) -> None:
        self._handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._handle.flush()

    def close(self) -> None:
        try:
            self._handle.close()
        except Exception:
            LOGGER.exception("Failed to close checkpoint writer for %s", self.path)


def _translate_example_sentences(
    example: BenchmarkExample,
    model_spec: str,
    cache: Optional[ResponseCache],
    checkpoint_writer: Optional[JsonlCheckpointWriter] = None,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for sentence in example.sentences:
        llm_result = run_llm_sentence_translation(
            sentence["text"], model_spec=model_spec, cache=cache
        )
        row = _build_sentence_row(
            example=example,
            sentence=sentence,
            llm_result=llm_result,
            model_spec=model_spec,
        )
        rows.append(row)
        if checkpoint_writer:
            checkpoint_writer.write(row)
    return rows


def _build_sentence_row(
    example: BenchmarkExample,
    sentence: Dict[str, object],
    llm_result: Dict[str, object],
    model_spec: str,
) -> Dict[str, object]:
    translation = llm_result.get("translation")
    error = llm_result.get("error")

    validators: Dict[str, bool] = {}
    if translation and not error:
        for name, fn in VALIDATORS.items():
            try:
                validators[name] = bool(fn(translation))
            except Exception:
                validators[name] = False

    parsing_metrics = None
    gold = sentence.get("gold_fol")
    if translation and gold:
        try:
            parsing_metrics = evaluate_parsing_pair(translation, gold)
        except Exception:
            parsing_metrics = None

    return {
        "story_id": example.story_id,
        "example_id": example.example_id,
        "label": example.label,
        "sentence_type": sentence.get("type"),
        "sentence_index": sentence.get("index"),
        "sentence": sentence.get("text"),
        "gold_fol": gold,
        "model": model_spec,
        "translation": translation,
        "error": error,
        "validators": validators,
        "parsing_metrics": parsing_metrics,
        "raw_text": llm_result.get("raw_text"),
        "raw_response": llm_result.get("raw_response"),
    }


def _translate_sentences_parallel(
    examples: Sequence[BenchmarkExample],
    model_spec: str,
    cache: Optional[ResponseCache],
    max_workers: int,
    show_progress: bool,
    log_every: int = 25,
    checkpoint_writer: Optional[JsonlCheckpointWriter] = None,
) -> List[Dict[str, object]]:
    jobs: List[Tuple[int, BenchmarkExample, Dict[str, object]]] = []
    for example in examples:
        for sentence in example.sentences:
            jobs.append((len(jobs), example, sentence))

    total = len(jobs)
    results: List[Optional[Dict[str, object]]] = [None] * total
    progress: Optional[tqdm] = None
    if show_progress:
        progress = tqdm(total=total, unit="sentence", desc="LLM", leave=False)

    log_every = max(1, log_every)
    LOGGER.info(
        "Dispatching %d sentences with max_workers=%d (log_every=%d)",
        total,
        max_workers,
        log_every,
    )
    completed = 0
    next_write_idx = 0

    def _task(job: Tuple[int, BenchmarkExample, Dict[str, object]]):
        idx, example, sentence = job
        llm_result = run_llm_sentence_translation(
            sentence["text"], model_spec=model_spec, cache=cache
        )
        row = _build_sentence_row(example, sentence, llm_result, model_spec)
        return idx, row

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_task, job): job[0] for job in jobs}
        pending: Dict[int, Dict[str, object]] = {}
        for future in as_completed(future_map):
            idx, row = future.result()
            results[idx] = row
            pending[idx] = row
            completed += 1
            if completed % log_every == 0 or completed == total:
                LOGGER.info("Completed %d/%d sentence translations", completed, total)
            while next_write_idx in pending:
                if checkpoint_writer:
                    checkpoint_writer.write(pending[next_write_idx])
                pending.pop(next_write_idx)
                next_write_idx += 1
            if progress is not None:
                progress.update(1)

    if progress is not None:
        progress.close()

    return [row for row in results if row is not None]


def _resolve_concurrency(max_concurrency: int, rpm: Optional[int]) -> int:
    max_concurrency = max(1, max_concurrency)
    if rpm and rpm > 0:
        derived = max(1, math.ceil(rpm / 60))
        max_concurrency = max(max_concurrency, derived)
    return max_concurrency


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
    unit: str = "example",
    max_concurrency: int = 1,
    checkpoint_writer: Optional[JsonlCheckpointWriter] = None,
) -> List[Dict[str, object]]:
    loader = get_dataset_loader(dataset)
    cache = ResponseCache() if use_cache else None

    if mode == "translation" and unit == "sentence" and max_concurrency > 1:
        examples: List[BenchmarkExample] = []
        total_sentences = 0
        for idx, example in enumerate(loader.iter_examples(split)):
            if limit is not None and idx >= limit:
                break
            examples.append(example)
            total_sentences += sum(1 for _ in example.sentences)
        LOGGER.info(
            "Running sentence-level translation on %d examples (%d sentences) with concurrency=%d",
            len(examples),
            total_sentences,
            max_concurrency,
        )
        log_every = max(1, total_sentences // 10) if total_sentences else 1
        return _translate_sentences_parallel(
            examples=examples,
            model_spec=model_spec,
            cache=cache,
            max_workers=max_concurrency,
            show_progress=show_progress,
            log_every=log_every,
            checkpoint_writer=checkpoint_writer,
        )

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
                if unit == "sentence":
                    new_rows = _translate_example_sentences(
                        example,
                        model_spec=model_spec,
                        cache=cache,
                        checkpoint_writer=checkpoint_writer,
                    )
                    rows.extend(new_rows)
                    if progress is not None:
                        progress.update(1)
                    continue
                result = run_llm_translation(
                    example, model_spec=model_spec, cache=cache
                )
            else:
                result = run_llm_entailment(example, model_spec=model_spec, cache=cache)
                result["label"] = example.label
            rows.append(result)
            if checkpoint_writer:
                checkpoint_writer.write(result)
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
        "--unit",
        choices=["example", "sentence"],
        default="example",
        help="Granularity for translation mode (default: example)",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model spec in form provider:model (e.g., openai:gpt-4o-mini)",
    )
    parser.add_argument(
        "--requests-per-minute",
        type=int,
        default=None,
        help="Optional RPM budget to derive concurrency",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=1,
        help="Maximum parallel LLM calls (default: 1)",
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
    parser.add_argument(
        "--checkpoint-jsonl",
        type=Path,
        default=None,
        help="Optional path to write incremental progress (overwritten each run)",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity for troubleshooting (default: WARNING)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Optional path to append detailed logs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging_kwargs = {
        "level": getattr(logging, args.log_level.upper(), logging.WARNING),
        "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    }
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        logging_kwargs["filename"] = args.log_file
        logging_kwargs["filemode"] = "a"
    logging.basicConfig(**logging_kwargs)

    show_progress = (not args.no_progress) and sys.stderr.isatty()
    checkpoint_path = args.checkpoint_jsonl or args.output_jsonl
    checkpoint_writer: Optional[JsonlCheckpointWriter] = None
    if checkpoint_path:
        checkpoint_writer = JsonlCheckpointWriter(checkpoint_path)
        LOGGER.info("Checkpointing incremental progress to %s", checkpoint_path)
    try:
        rows = run(
            dataset=args.dataset,
            split=args.split,
            mode=args.mode,
            model_spec=args.model,
            limit=args.limit,
            use_cache=args.cache,
            show_progress=show_progress,
            unit=args.unit,
            max_concurrency=_resolve_concurrency(
                args.max_concurrency, args.requests_per_minute
            ),
            checkpoint_writer=checkpoint_writer,
        )
    finally:
        if checkpoint_writer:
            checkpoint_writer.close()

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
