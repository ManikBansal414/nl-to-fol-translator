from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from translator import translate_sentence
from method_fomaster.validator import validate as validate_fomaster
from method_lark.validator import validate as validate_lark
from method_nltk.validator import validate as validate_nltk

from .fol_analysis import evaluate_parsing_pair
from .metrics import aggregate_example_rows, aggregate_translation_rows
from .registry import get_dataset_loader

VALIDATORS = {
    "lark": validate_lark,
    "nltk": validate_nltk,
    "fomaster": validate_fomaster,
}


def translate_and_validate(text: str, gold_fol: str | None = None) -> Dict[str, object]:
    """Translate a sentence and run secondary validators."""
    text = text.strip()
    if not text:
        return {
            "translation": None,
            "error": "[ERROR] Empty sentence",
            "validators": {},
            "parsing_metrics": None,
        }

    fol = translate_sentence(text)
    if fol.startswith("[ERROR]"):
        return {
            "translation": None,
            "error": fol,
            "validators": {},
            "parsing_metrics": None,
        }

    validators: Dict[str, bool] = {}
    for name, fn in VALIDATORS.items():
        try:
            validators[name] = bool(fn(fol))
        except Exception:
            validators[name] = False

    parsing_metrics = None
    if gold_fol:
        try:
            parsing_metrics = evaluate_parsing_pair(fol, gold_fol)
        except Exception:
            parsing_metrics = None

    return {
        "translation": fol,
        "error": None,
        "validators": validators,
        "parsing_metrics": parsing_metrics,
    }


def _translate_sentences(example) -> List[Dict[str, object]]:
    sentence_rows: List[Dict[str, object]] = []
    for sentence in example.sentences:
        outcome = translate_and_validate(
            sentence["text"], gold_fol=sentence.get("gold_fol")
        )
        sentence_rows.append(
            {
                "story_id": example.story_id,
                "example_id": example.example_id,
                "label": example.label,
                "sentence_type": sentence["type"],
                "sentence_index": sentence["index"],
                "sentence": sentence["text"],
                "gold_fol": sentence.get("gold_fol"),
                **outcome,
            }
        )
    return sentence_rows


def _translate_example(example) -> Dict[str, object]:
    sentences = _translate_sentences(example)
    return {
        "story_id": example.story_id,
        "example_id": example.example_id,
        "label": example.label,
        "sentences": sentences,
    }


def run(
    dataset: str, split: str, limit: int | None, unit: str = "sentence"
) -> List[Dict[str, object]]:
    loader = get_dataset_loader(dataset)
    rows: List[Dict[str, object]] = []
    for idx, example in enumerate(loader.iter_examples(split)):
        if limit is not None and idx >= limit:
            break
        if unit == "example":
            rows.append(_translate_example(example))
        else:
            rows.extend(_translate_sentences(example))
    return rows


def dump_jsonl(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def dump_summary(path: Path, summary: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run NL→FOL translation benchmarks on available datasets."
    )
    parser.add_argument(
        "--dataset", default="folio", help="Dataset name (default: folio)"
    )
    parser.add_argument(
        "--split",
        default="validation",
        help="Dataset split to evaluate (default: validation)",
    )
    parser.add_argument(
        "--unit",
        choices=["sentence", "example"],
        default="sentence",
        help="Granularity for outputs (default: sentence)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of examples to process",
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=None,
        help="Optional path to write per-sentence results as JSONL",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional path to write aggregate summary as JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = run(dataset=args.dataset, split=args.split, limit=args.limit, unit=args.unit)
    if args.unit == "example":
        summary = aggregate_example_rows(rows)
    else:
        summary = aggregate_translation_rows(rows)

    print(f"Dataset: {args.dataset} | Split: {args.split}")
    if args.unit == "example":
        print(f"Examples processed: {summary.get('total_examples', len(rows))}")
    print(f"Sentences processed: {summary['total_sentences']}")
    print(f"Successful translations: {summary['translations']}")
    print(f"Success rate: {summary['translation_rate']:.2%}")
    if summary["validators"]:
        print("Validator breakdown:")
        for name, counts in summary["validators"].items():
            total = counts["passed"] + counts["failed"]
            rate = (counts["passed"] / total) if total else 0.0
            print(f"  - {name}: {counts['passed']}/{total} ({rate:.2%})")

    if args.output_jsonl:
        dump_jsonl(args.output_jsonl, rows)
        print(f"Wrote detailed rows to {args.output_jsonl}")

    if args.summary_json:
        dump_summary(args.summary_json, summary)
        print(f"Wrote summary to {args.summary_json}")


if __name__ == "__main__":
    main()
